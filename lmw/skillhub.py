"""Install skills from GitHub repositories:  lmw skills add https://github.com/owner/repo

Works with any repo that keeps skills as folders with a SKILL.md (the Claude Code / Anthropic skill layout).
Each skill is converted to LMW's format and saved in ~/.lmw/skills/<name>/ — nothing is added to the lmw
repository, and nothing from the downloaded repo is ever executed (scripts and binaries are ignored; only
SKILL.md and a few sibling .md docs are read).

Installed skills are "library" skills: lmw uses one only when the request clearly matches it
(see skills.select_skills), and the built-in skills always come first.
"""

from __future__ import annotations

import fnmatch
import io
import json
import re
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import netutil
from . import __version__
from .skills import user_skills_dir

MAX_ZIP = 250 * 1024 * 1024
MAX_SKILL_FILE = 400 * 1024
MAX_BODY = 24000
MAX_REF = 12000
MAX_REFS = 6
HIDDEN_NEVER = {"node_modules", ".git", "__pycache__", "backup", "backups", "dist", "build", "venv", ".venv", "site-packages"}
TEMPLATE_NAMES = {"template", "template-skill", "skill-template", "example-skill", "hello-world"}
RAW_KEYS = {"argument-hint", "argument_hint", "description", "name"}
SKIP_DOCS = {"skill.md", "readme.md", "license.md", "changelog.md", "contributing.md", "code_of_conduct.md"}

# the sources the user asked for (lmw skills add --defaults)
DEFAULT_SOURCES = ["bear2u/my-skills", "ComposioHQ/awesome-claude-skills", "alirezarezvani/claude-skills"]

STOP = set("""
about above after again against agent agents also always analysis analyze analyzing and any are around based because been before being below
between both build builds building can claude code codes comprehensive complete could create creates creating current data does doing done
each either else enable enables ensure even every example examples expert features file files find first following for from full generate
generates generating get gets give gives good great guide guides has have help helps here high how however include includes including into
its just keep like look looking make makes making many may more most much must need needs new not now off once one only other our out over
own per perform please provide provides providing real really run runs same see set should show simple since skill skills some specific such
support supports take tasks than that the their them then there these they this those through tool tools top two under until use used user
users uses using very want was way ways well were what when where whether which while who will with within without work works workflow would
you your professional production quality best practices automatically automate automated advanced various multiple different specific senior says asks mentions wants why apply applies official sort artifact having benefit
""".split())


# ------------------------------------------------------------------ sources

def _strip_git(repo: str) -> str:
    return repo[:-4] if repo.endswith(".git") else repo


def parse_source(arg: str) -> Tuple[str, str, str, str]:
    """'owner/repo', a github.com URL (also .../tree/<ref>/<folder>) or a github search link -> (owner, repo, ref, folder)."""
    a = arg.strip()
    if not a:
        raise ValueError("GitHub 주소가 비어 있습니다")
    if "://" not in a and a.count("/") == 1 and not a.startswith("github.com"):
        owner, repo = a.split("/")
        return owner, _strip_git(repo), "HEAD", ""
    if "://" not in a:
        a = "https://" + a
    u = urllib.parse.urlparse(a)
    if u.netloc.lower() not in ("github.com", "www.github.com"):
        raise ValueError("github.com 주소만 지원합니다: %s" % arg)
    q = urllib.parse.parse_qs(u.query).get("q")
    if u.path.rstrip("/") == "/search" and q:  # a search link such as ?q=owner%2Frepo
        m = re.fullmatch(r"\s*([\w.-]+)/([\w.-]+)\s*", q[0])
        if not m:
            raise ValueError("검색 주소에서 저장소를 찾지 못했습니다: %s" % arg)
        return m.group(1), m.group(2), "HEAD", ""
    parts = [p for p in u.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("owner/repo 형식의 주소가 필요합니다: %s" % arg)
    owner, repo = parts[0], _strip_git(parts[1])
    ref, folder = "HEAD", ""
    if len(parts) >= 4 and parts[2] in ("tree", "blob"):
        ref, folder = parts[3], "/".join(parts[4:])
    return owner, repo, ref, folder


def _get(url: str, timeout: float = 30) -> urllib.request.addinfourl:
    req = urllib.request.Request(url, headers={"User-Agent": "lmw-cli/%s" % __version__, "Accept": "*/*"})
    return netutil.urlopen(req, timeout=timeout)  # type: ignore[return-value]


def repo_license(owner: str, repo: str) -> str:
    try:
        with _get("https://api.github.com/repos/%s/%s" % (owner, repo), 15) as r:
            lic = (json.loads(r.read().decode("utf-8")).get("license") or {}).get("spdx_id")
        return lic if lic and lic != "NOASSERTION" else "unknown"
    except Exception:
        return "unknown"


def download(owner: str, repo: str, ref: str, log: Callable[[str], None]) -> zipfile.ZipFile:
    url = "https://codeload.github.com/%s/%s/zip/%s" % (owner, repo, urllib.parse.quote(ref, safe="/"))
    log("내려받는 중: %s/%s" % (owner, repo))
    tmp = tempfile.TemporaryFile()
    total = 0
    with _get(url, 60) as r:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_ZIP:
                raise ValueError("저장소가 너무 큽니다 (%d MB 초과)" % (MAX_ZIP // 1048576))
            tmp.write(chunk)
    tmp.seek(0)
    log("  %.1f MB" % (total / 1048576))
    return zipfile.ZipFile(tmp)


# --------------------------------------------------------------- conversion

def parse_loose(text: str) -> Tuple[Dict[str, object], str]:
    """Frontmatter as found in the wild: quoted values, folded/literal blocks (> |), block lists, nested maps."""
    t = text.lstrip("﻿")
    if not t.startswith("---"):
        return {}, t
    lines = t.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, t
    meta: Dict[str, object] = {}
    i = 1
    while i < end:
        line = lines[i]
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        i += 1
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", ">-", ">+", "|", "|-", "|+") or val == "":
            block = []
            while i < end and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i])
                i += 1
            items = [b.strip()[2:].strip() for b in block if b.strip().startswith("- ")]
            if val == "" and items:
                meta[key] = [x.strip("'\"") for x in items]
            elif val == "":
                meta[key] = {"_raw": "\n".join(block)}  # nested map (metadata:, requires: ...)
            else:
                text_block = [b.strip() for b in block]
                meta[key] = (" " if val.startswith(">") else "\n").join(x for x in text_block if x).strip()
            continue
        if val.startswith("[") and val.endswith("]") and key not in RAW_KEYS:
            meta[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
        elif key in RAW_KEYS and val.startswith("["):
            meta[key] = val  # "[pr-number]" is a hint to show, not a list
        elif len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            meta[key] = val[1:-1].replace('\\"', '"')
        else:
            meta[key] = val
    return meta, "\n".join(lines[end + 1:]).strip("\n")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:60] or "skill"


def _words(text: str) -> List[str]:
    return [w.lower().strip(".-+#") for w in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", text)]


def derive_triggers(name: str, description: str, tags: Optional[List[str]] = None, limit: int = 16) -> List[str]:
    """Imported skills have no triggers: build them from the name, tags and the description's own keywords."""
    score: Counter = Counter()
    order: Dict[str, int] = {}

    def add(term: str, weight: int) -> None:
        term = re.sub(r"\s+", " ", term.strip().lower().strip("\"'`*_.,:;()"))
        if len(term) < 3 or len(term) > 32 or term in STOP or term.startswith(("the user", "user ", "a user")):
            return
        if term.isascii() and all(w in STOP for w in re.split(r"[\s-]+", term)):
            return
        order.setdefault(term, len(order))
        score[term] += weight

    toks = [t for t in re.split(r"[-_\s]+", name.lower()) if t]
    for t in toks:
        add(t, 4)
    if len(toks) > 1:
        add(" ".join(toks), 5)
    for t in tags or []:
        add(str(t), 4)
    for m in re.finditer(r"(?:use (?:this skill |it )?(?:when|for|to)|triggers?(?: on| when| phrases?)?|keywords?|when (?:the )?user (?:asks|mentions|says|wants))\s*:?\s*([^.\n]{8,300})",
                         description, re.I):
        clause = m.group(1)
        for part in re.split(r",|;| or | and |\"|“|”", clause):
            add(part, 3)
        for w in _words(clause):  # the clause is about the topic: its single words count too
            add(w, 2)
    for m in re.finditer(r'"([^"]{3,40})"|“([^”]{3,40})”', description):
        add(m.group(1) or m.group(2), 3)
    # elsewhere in the description only words that look like names/technologies count (React, WCAG, Next.js, C#, k8s):
    # plain lowercase words ("having", "artifact") would make a skill match unrelated requests
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][A-Za-z0-9+#.]*[A-Z0-9+#.][A-Za-z0-9+#.]*|[A-Z][a-z]{3,}|[a-z]+\d[a-z0-9]*)\b", description):
        add(m.group(1), 2)
    for w in re.findall(r"[가-힣]{2,}", description):
        add(w, 2)
    ranked = sorted(score, key=lambda t: (-score[t], order[t]))
    return ranked[:limit]


def first_paragraph(body: str) -> str:
    for block in re.split(r"\n\s*\n", body):
        b = re.sub(r"^#+\s*", "", block.strip())
        if b and not b.startswith(("```", "|", "---")):
            return re.sub(r"\s+", " ", b)[:300]
    return ""


def clamp(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    cut = cut[: max(cut.rfind("\n\n"), int(limit * 0.8))]
    return cut.rstrip() + "\n\n[… shortened by lmw]"


class Found:
    def __init__(self, path: str, meta: Dict[str, object], body: str, docs: Dict[str, str]):
        self.path, self.meta, self.body, self.docs = path, meta, body, docs
        self.name = str(meta.get("name") or Path(path.rstrip("/")).name or "skill")
        self.slug = slugify(self.name)
        d = meta.get("description")
        self.description = re.sub(r"\s+", " ", str(d if isinstance(d, str) else "") or first_paragraph(body)).strip()


def _hidden_rank(path: str) -> Tuple[int, int, int]:
    """Prefer copies outside tool folders (.claude/, .cursor/ ...), then shorter paths."""
    hidden = any(p.startswith(".") for p in path.split("/") if p)
    return (1 if hidden else 0, path.count("/"), len(path))


def find_skills(zf: zipfile.ZipFile, folder: str = "", include_connectors: bool = False) -> Tuple[List[Found], Counter]:
    names = zf.namelist()
    skipped: Counter = Counter()
    if not names:
        return [], skipped
    root = names[0].split("/")[0] + "/"
    prefix = root + folder.strip("/") + "/" if folder.strip("/") else root
    by_slug: Dict[str, Found] = {}
    for n in names:
        if not n.startswith(prefix) or not n.lower().endswith("/skill.md"):
            continue
        rel = n[len(root):-len("SKILL.md")]
        parts = [p for p in rel.split("/") if p]
        if any(p in HIDDEN_NEVER or p == ".." for p in parts):
            continue
        info = zf.getinfo(n)
        if info.file_size > MAX_SKILL_FILE:
            skipped["too big"] += 1
            continue
        text = zf.read(n).decode("utf-8", "replace")
        meta, body = parse_loose(text)
        if not body.strip():
            skipped["empty"] += 1
            continue
        folder_name = parts[-1] if parts else ""
        if folder_name.lower() in TEMPLATE_NAMES or str(meta.get("name", "")).lower() in TEMPLATE_NAMES:
            skipped["template"] += 1
            continue
        if not include_connectors and (meta.get("requires") or "composio-skills" in parts):
            skipped["needs a connector/MCP account"] += 1  # e.g. Composio app integrations: useless offline
            continue
        base = root + rel
        docs: Dict[str, str] = {}
        for m in names:
            if not m.startswith(base) or m == n or m.endswith("/"):
                continue
            tail = m[len(base):]
            low = tail.lower()
            if not low.endswith(".md") or zf.getinfo(m).file_size > MAX_SKILL_FILE:
                continue
            first = tail.split("/")[0].lower()
            direct = "/" not in tail
            if (direct and low not in SKIP_DOCS) or (first in ("reference", "references", "docs") and tail.count("/") == 1):
                docs[Path(tail).stem] = zf.read(m).decode("utf-8", "replace")
            if len(docs) >= MAX_REFS:
                break
        f = Found(rel, meta, body, docs)
        old = by_slug.get(f.slug)
        if old is None or _hidden_rank(f.path) < _hidden_rank(old.path):
            by_slug[f.slug] = f
        else:
            skipped["duplicate"] += 1
    return sorted(by_slug.values(), key=lambda f: f.slug), skipped


def render_skill(f: Found, source: str, license_id: str) -> Tuple[str, Dict[str, str]]:
    tags = f.meta.get("tags")
    tag_list = [str(t) for t in tags] if isinstance(tags, list) else (
        [t.strip() for t in tags.split(",")] if isinstance(tags, str) else [])
    triggers = derive_triggers(f.name, f.description, tag_list)
    desc = f.description[:400].replace("\n", " ")
    lic = str(f.meta.get("license") or "").split("\n")[0][:60]
    fm = ["---", "name: %s" % f.slug, "description: %s" % desc, "triggers: [%s]" % ", ".join(triggers),
          "priority: 30", "library: true", "source: %s" % source, "license: %s" % (lic or license_id), "---"]
    note = "(Installed by `lmw skills add` from %s. Scripts and other files this text mentions are not installed — " \
           "use your own tools instead.)\n\n" % source
    text = "\n".join(fm) + "\n" + note + clamp(f.body, MAX_BODY) + "\n"
    refs: Dict[str, str] = {}
    for stem, doc in f.docs.items():
        meta, body = parse_loose(doc)
        rname = slugify(stem)
        rdesc = (str(meta.get("description") or "") or first_paragraph(body) or stem)[:200].replace("\n", " ")
        rtrig = derive_triggers(stem, rdesc, limit=10) or [rname]
        refs[rname + ".md"] = "---\nname: %s\ndescription: %s\ntriggers: [%s]\n---\n%s\n" % (
            rname, rdesc, ", ".join(rtrig), clamp(body, MAX_REF))
    return text, refs


# ------------------------------------------------------------------ install

def installed_registry(dest: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    f = (dest or user_skills_dir()) / ".installed.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_registry(reg: Dict[str, Dict[str, str]], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / ".installed.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")


def matches(f: Found, only: Optional[List[str]]) -> bool:
    if not only:
        return True
    hay = (f.slug + " " + f.description + " " + f.path).lower()
    for pat in only:
        p = pat.strip().lower()
        if p and (fnmatch.fnmatch(f.slug, p) or p in hay):
            return True
    return False


def install(source: str, dest: Optional[Path] = None, only: Optional[List[str]] = None,
            include_connectors: bool = False, limit: int = 0, dry_run: bool = False,
            log: Callable[[str], None] = print, zf: Optional[zipfile.ZipFile] = None, license_id: str = "") -> List[str]:
    """Download `source` and install its skills. Returns the installed names."""
    dest = dest or user_skills_dir()
    owner, repo, ref, folder = parse_source(source)
    label = "%s/%s" % (owner, repo)
    lic = license_id or ("unknown" if zf is not None else repo_license(owner, repo))
    zf = zf or download(owner, repo, ref, log)
    found, skipped = find_skills(zf, folder, include_connectors)
    chosen = [f for f in found if matches(f, only)]
    if limit and len(chosen) > limit:
        chosen = chosen[:limit]
    if not found:
        log("SKILL.md 가 있는 폴더를 찾지 못했습니다")
        return []
    reg = installed_registry(dest)
    done: List[str] = []
    for f in chosen:
        if reg.get(f.slug) and reg[f.slug].get("source") != label and (dest / f.slug).exists():
            f.slug = slugify(owner + "-" + f.slug)  # same name from another source: keep both
        if dry_run:
            done.append(f.slug)
            continue
        text, refs = render_skill(f, label, lic)
        d = dest / f.slug
        if d.exists():
            for old in (d / "reference").glob("*.md") if (d / "reference").is_dir() else []:
                old.unlink()
        (d / "reference").mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(text, encoding="utf-8")
        for fname, content in refs.items():
            (d / "reference" / fname).write_text(content, encoding="utf-8")
        (d / "SOURCE.txt").write_text("%s\nfolder: %s\nlicense: %s\ninstalled: %s\n" % (
            "https://github.com/" + label, f.path, lic, time.strftime("%Y-%m-%d %H:%M")), encoding="utf-8")
        reg[f.slug] = {"source": label, "path": f.path, "license": lic, "installed": time.strftime("%Y-%m-%d")}
        done.append(f.slug)
    if not dry_run:
        _save_registry(reg, dest)
    extra = ", ".join("%s %d" % (k, v) for k, v in skipped.items())
    log("%s: 스킬 %d개 %s%s%s" % (label, len(done), "(미리보기)" if dry_run else "설치",
                               "  · 라이선스 %s" % lic if lic != "unknown" else "  · 라이선스 정보 없음",
                               "  · 건너뜀: " + extra if extra else ""))
    return done


def remove(names: List[str], dest: Optional[Path] = None) -> List[str]:
    """Remove installed skills by name, or 'owner/repo' for everything from that source. Only touches skills lmw installed."""
    import shutil
    dest = dest or user_skills_dir()
    reg = installed_registry(dest)
    gone: List[str] = []
    for n in names:
        keys = [k for k, v in reg.items() if k == slugify(n) or v.get("source", "").lower() == n.lower()]
        for k in keys:
            d = dest / k
            if d.is_dir() and (d / "SOURCE.txt").is_file():  # never delete folders lmw did not create
                shutil.rmtree(d)
            reg.pop(k, None)
            gone.append(k)
    if gone:
        _save_registry(reg, dest)
    return gone


def listing(dest: Optional[Path] = None) -> List[Dict[str, str]]:
    reg = installed_registry(dest)
    return [dict(v, name=k) for k, v in sorted(reg.items())]


# ---------------------------------------------------------------- commands

ADMIN = ("add", "install", "remove", "rm", "uninstall", "list", "installed")


def run_command(words: List[str], log: Callable[[str], None] = print, dest: Optional[Path] = None) -> Optional[int]:
    """`lmw skills add|remove|list ...` (also `/skills add ...` inside lmw). None = not an install command."""
    if not words or words[0].lower() not in ADMIN:
        return None
    cmd, rest = words[0].lower(), words[1:]
    if cmd in ("list", "installed"):
        rows = listing(dest)
        if not rows:
            log("설치한 외부 스킬이 없습니다.  예:  lmw skills add https://github.com/owner/repo   (또는 --defaults)")
            return 0
        by_src: Dict[str, List[str]] = {}
        for r in rows:
            by_src.setdefault(r["source"], []).append(r["name"])
        for src, names in by_src.items():
            log("%s (%d개)  %s" % (src, len(names), ", ".join(names[:12]) + (" …" if len(names) > 12 else "")))
        return 0
    if cmd in ("remove", "rm", "uninstall"):
        gone = remove(rest, dest)
        log("삭제: %s" % (", ".join(gone) if gone else "없음 (lmw 가 설치한 스킬만 지울 수 있습니다)"))
        return 0 if gone else 1
    only: List[str] = []
    sources: List[str] = []
    flags = {"defaults": False, "connectors": False, "dry": False}
    limit = 0
    i = 0
    while i < len(rest):
        w = rest[i]
        if w == "--only" and i + 1 < len(rest):
            only += [x for x in rest[i + 1].split(",") if x]
            i += 1
        elif w == "--limit" and i + 1 < len(rest) and rest[i + 1].isdigit():
            limit = int(rest[i + 1])
            i += 1
        elif w == "--defaults":
            flags["defaults"] = True
        elif w in ("--connectors", "--all"):
            flags["connectors"] = True
        elif w in ("--dry-run", "--preview"):
            flags["dry"] = True
        else:
            sources.append(w)
        i += 1
    if flags["defaults"]:
        sources += DEFAULT_SOURCES
    if not sources:
        log("사용법:  skills add <GitHub 주소> [--only 이름,이름] [--limit N] [--dry-run]   |   skills add --defaults")
        return 2
    log("외부 스킬은 모델에게 주는 지침으로 들어갑니다 — 신뢰하는 저장소만 설치하세요 (스크립트는 설치·실행하지 않습니다)")
    total, failed = 0, 0
    for src in sources:
        try:
            total += len(install(src, dest, only or None, flags["connectors"], limit, flags["dry"], log))
        except Exception as e:  # network, bad address, bad zip …
            failed += 1
            log("%s: 실패 — %s" % (src, e))
    if total and not flags["dry"]:
        log("완료: 스킬 %d개. 요청이 스킬과 뚜렷하게 맞을 때만 사용됩니다 (확인: lmw skills \"요청 문장\")" % total)
    return 0 if not failed else 1


# ------------------------------------------------- agents and slash commands

NOT_DOCS = {"readme", "index", "license", "changelog", "contributing", "code_of_conduct", "security"}
SKIP_DOC_DIRS = {"tests", "test", "examples", "example", "fixtures", "__tests__", "node_modules", "docs", "doc", "translations"}


def user_dir(kind: str) -> Path:
    import os
    return Path(os.environ.get("LMW_HOME") or (Path.home() / ".lmw")) / kind


def find_docs(zf: zipfile.ZipFile, kind: str, folder: str = "") -> List[Tuple[str, str, str]]:
    """Markdown files directly inside a folder named `kind` ("agents" or "commands"): [(slug, path, text)].
    Copies under tool folders (.claude/, .cursor/ …) or translations lose to the main copy."""
    names = zf.namelist()
    if not names:
        return []
    root = names[0].split("/")[0] + "/"
    prefix = root + (folder.strip("/") + "/" if folder.strip("/") else "")
    pat = re.compile(r"^(?:.*/)?%s/([^/]+)\.md$" % re.escape(kind))
    found: Dict[str, Tuple[str, str, str]] = {}
    for n in names:
        if not n.startswith(prefix):
            continue
        rel = n[len(root):]
        m = pat.match(rel)
        if not m:
            continue
        parts = rel.split("/")[:-1]
        if any(x in HIDDEN_NEVER or x in SKIP_DOC_DIRS for x in parts) or m.group(1).lower() in NOT_DOCS:
            continue
        if zf.getinfo(n).file_size > MAX_SKILL_FILE:
            continue
        text = zf.read(n).decode("utf-8", "replace")
        meta, body = parse_loose(text)
        if not body.strip():
            continue
        if kind == "agents" and not (meta.get("name") or meta.get("description")):
            continue  # not an agent definition
        if kind == "commands" and not (meta.get("description") or "$ARGUMENTS" in body):
            continue
        slug = slugify(str(meta.get("name") or m.group(1)) if kind == "agents" else m.group(1))
        old = found.get(slug)
        if old is None or _hidden_rank(rel) < _hidden_rank(old[1]):
            found[slug] = (slug, rel, text)
    return sorted(found.values())


def _doc_registry(kind: str) -> Dict[str, Dict[str, str]]:
    try:
        return json.loads((user_dir(kind) / ".installed.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def install_docs(kind: str, source: str, zf: zipfile.ZipFile, label: str, lic: str, only: Optional[List[str]] = None,
                 folder: str = "", dry_run: bool = False, log: Callable[[str], None] = print) -> List[str]:
    docs = find_docs(zf, kind, folder)
    if only:
        docs = [d for d in docs if any(fnmatch.fnmatch(d[0], o.lower()) or o.lower() in d[0] for o in only)]
    dest = user_dir(kind)
    reg = _doc_registry(kind)
    done: List[str] = []
    for slug, rel, text in docs:
        if dry_run:
            done.append(slug)
            continue
        meta, body = parse_loose(text)
        desc = " ".join(str(meta.get("description") or first_paragraph(body)).split())[:400]
        fm = ["---", "name: %s" % slug, "description: %s" % desc]
        if kind == "agents":
            tools = meta.get("tools")
            fm.append("tools: %s" % (", ".join(tools) if isinstance(tools, list) else str(tools or "")))
        else:
            fm.append("argument-hint: %s" % str(meta.get("argument-hint") or meta.get("argument_hint") or "").replace("\n", " "))
        fm += ["source: %s" % label, "license: %s" % lic, "---"]
        dest.mkdir(parents=True, exist_ok=True)
        (dest / (slug + ".md")).write_text("\n".join(fm) + "\n" + clamp(body, 16000) + "\n", encoding="utf-8")
        reg[slug] = {"source": label, "path": rel, "license": lic, "installed": time.strftime("%Y-%m-%d")}
        done.append(slug)
    if done and not dry_run:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / ".installed.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    return done


def remove_docs(kind: str, names: List[str]) -> List[str]:
    dest = user_dir(kind)
    reg = _doc_registry(kind)
    gone: List[str] = []
    for n in names:
        for k in [k for k, v in reg.items() if k == slugify(n) or v.get("source", "").lower() == n.lower()]:
            f = dest / (k + ".md")
            if f.is_file():
                f.unlink()
            reg.pop(k, None)
            gone.append(k)
    if gone:
        (dest / ".installed.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    return gone


def install_pack(source: str, kinds: Tuple[str, ...] = ("skills", "agents", "commands"), only: Optional[List[str]] = None,
                 dry_run: bool = False, log: Callable[[str], None] = print, zf: Optional[zipfile.ZipFile] = None) -> Dict[str, List[str]]:
    """One download, everything useful in it: skills, agents, slash commands (+ a hint when it has MCP configs)."""
    owner, repo, ref, folder = parse_source(source)
    label = "%s/%s" % (owner, repo)
    lic = "unknown" if zf is not None else repo_license(owner, repo)
    zf = zf or download(owner, repo, ref, log)
    out: Dict[str, List[str]] = {}
    if "skills" in kinds:
        out["skills"] = install(source, only=only, dry_run=dry_run, log=log, zf=zf, license_id=lic)
    for kind in ("agents", "commands"):
        if kind in kinds:
            out[kind] = install_docs(kind, source, zf, label, lic, only, folder, dry_run, log)
            if out[kind]:
                log("%s: %s %d개 %s" % (label, "에이전트" if kind == "agents" else "슬래시 명령", len(out[kind]), "(미리보기)" if dry_run else "설치"))
    cfgs = [n for n in zf.namelist() if re.search(r"mcp-?configs?/[^/]*\.json$|mcp-servers\.json$", n)]
    if cfgs:
        log("MCP 서버 목록 발견: %s → 도구로 쓰려면  lmw mcp import https://github.com/%s/blob/HEAD/%s" % (
            cfgs[0].split("/", 1)[1], label, cfgs[0].split("/", 1)[1]))
    return out


# ------------------------------------------------------------ awesome list

AWESOME_CSV = "https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/THE_RESOURCES_TABLE_NEW.csv"
AWESOME_CREDIT = "목록 출처: github.com/hesreallyhim/awesome-claude-code (CC BY-NC-ND 4.0) — 내용을 저장·복제하지 않고 그때그때 읽어 보여줍니다"


def awesome_rows(max_age_hours: float = 24) -> List[Dict[str, str]]:
    import csv
    cache = user_dir("cache") / "awesome.csv"
    if not (cache.is_file() and time.time() - cache.stat().st_mtime < max_age_hours * 3600):
        with _get(AWESOME_CSV, 30) as r:
            data = r.read().decode("utf-8", "replace")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(data, encoding="utf-8")
    return list(csv.DictReader(io.StringIO(cache.read_text(encoding="utf-8"))))


def find_resources(query: str, limit: int = 12, rows: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
    rows = rows if rows is not None else awesome_rows()
    qw = set(re.findall(r"[a-z0-9+#.]{2,}|[가-힣]{2,}", query.lower()))
    scored = []
    for r in rows:
        if str(r.get("Active", "TRUE")).upper() == "FALSE":
            continue
        name = (r.get("Display Name") or "").lower()
        hay = " ".join([name, (r.get("Description") or "").lower(), (r.get("Category") or "").lower(), (r.get("Sub-Category") or "").lower()])
        score = sum((3 if w in name else 0) + (1 if w in hay else 0) for w in qw)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _s, r in scored[:limit]]


PACK_ADMIN = ("add", "find")


def run_pack_command(cmd: str, words: List[str], log: Callable[[str], None] = print) -> int:
    """`lmw add <github url> [--only a,b] [--skills|--agents|--cmds] [--dry-run]`   `lmw find <keywords>`"""
    if cmd == "find":
        if not words:
            log("사용법: find <찾을 것>   예: find security review   (awesome-claude-code 목록에서 검색)")
            return 2
        try:
            rows = find_resources(" ".join(words))
        except Exception as e:
            log("목록을 읽지 못했습니다: %s" % e)
            return 1
        if not rows:
            log("찾지 못했습니다. 영어 키워드로 다시 해보세요")
        for r in rows:
            log("[%s] %s — %s" % (r.get("Category", ""), r.get("Display Name", ""), " ".join((r.get("Description") or "").split())[:110]))
            log("    %s   (설치: add %s)" % (r.get("Link", ""), r.get("Link", "")))
        log(AWESOME_CREDIT)
        return 0 if rows else 1
    only: List[str] = []
    srcs: List[str] = []
    kinds: List[str] = []
    dry = False
    i = 0
    while i < len(words):
        w = words[i]
        if w == "--only" and i + 1 < len(words):
            only += [x for x in words[i + 1].split(",") if x]
            i += 1
        elif w in ("--skills", "--agents"):
            kinds.append(w[2:])
        elif w in ("--cmds", "--commands"):
            kinds.append("commands")
        elif w in ("--dry-run", "--preview"):
            dry = True
        else:
            srcs.append(w)
        i += 1
    if not srcs:
        log("사용법: add <GitHub 주소> [--only 이름,이름] [--skills|--agents|--cmds] [--dry-run]   (스킬·에이전트·슬래시 명령을 한 번에)")
        return 2
    log("외부 자료는 모델에게 주는 지침으로 들어갑니다 — 신뢰하는 저장소만 설치하세요 (스크립트는 설치·실행하지 않습니다)")
    bad = 0
    for src in srcs:
        try:
            res = install_pack(src, tuple(kinds) or ("skills", "agents", "commands"), only or None, dry, log)
        except Exception as e:
            bad += 1
            log("%s: 실패 — %s" % (src, e))
            continue
        if not any(res.values()):
            log("%s: 설치할 스킬·에이전트·명령을 찾지 못했습니다 (MCP 서버라면: mcp add <이름> -- <명령>)" % src)
            bad += 1
    return 1 if bad else 0


def run_docs_command(kind: str, words: List[str], log: Callable[[str], None] = print) -> int:
    """`agents|cmds list | add <url> | remove <name>` for sub-agents (kind="agents") or slash commands ("commands")."""
    from . import agents as agentlib, usercmds
    sub = words[0].lower() if words else "list"
    word = "agents" if kind == "agents" else "cmds"
    if sub == "add":
        return run_pack_command("add", words[1:] + ["--agents" if kind == "agents" else "--cmds"], log)
    if sub in ("remove", "rm"):
        gone = remove_docs(kind, words[1:])
        log("삭제: %s" % (", ".join(gone) if gone else "없음 (가져온 것만 지울 수 있습니다)"))
        return 0 if gone else 1
    if kind == "agents":
        rows = [(p.name, p.description, "읽기 전용" if p.read_only else "수정 가능") for p in agentlib.load_agents().values()]
        log("하위 에이전트 — 모델이 agent(이름, 작업) 으로 부릅니다")
    else:
        rows = [(c.name, c.description, c.hint) for c in usercmds.load().values()]
        log("가져온 슬래시 명령 — /이름 인자 (이름이 겹치면 /cmd 이름)")
    for n, d, extra in rows[:60]:
        log("  %-26s %s%s" % (n, d[:80], ("  [%s]" % extra) if extra else ""))
    if len(rows) > 60:
        log("  … 외 %d개" % (len(rows) - 60))
    if not rows:
        log("없습니다.  %s add <GitHub 주소>   예: %s add https://github.com/affaan-m/ecc" % (word, word))
    return 0
