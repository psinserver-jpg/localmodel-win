"""Tolerant parsers for model output. Small models deviate from formats, so every parser
has a fallback and never raises on malformed text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------- file blocks

_FILE_START = re.compile(r"^\s*={2,}\s*(FILE|EDIT)\s*:\s*(.+?)\s*={2,}\s*$", re.IGNORECASE)
_FILE_END = re.compile(r"^\s*={2,}\s*END\s*(FILE|EDIT)?\s*={2,}\s*$", re.IGNORECASE)
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")


@dataclass
class Edit:
    search: str
    replace: str


@dataclass
class FileBlock:
    path: str
    kind: str  # "file" or "edit"
    content: str = ""
    edits: List[Edit] = field(default_factory=list)
    closed: bool = True


@dataclass
class ParsedOutput:
    blocks: List[FileBlock]
    truncated: bool  # an unclosed FILE/EDIT block was found


def clean_path(raw: str) -> str:
    p = raw.strip().strip("`'\"*").strip()
    p = p.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def _strip_wrapping_fence(text: str) -> str:
    lines = text.split("\n")
    first = next((i for i, l in enumerate(lines) if l.strip()), None)
    last = next((i for i in range(len(lines) - 1, -1, -1) if lines[i].strip()), None)
    if first is None or last is None or first == last:
        return text
    if _FENCE.match(lines[first]) and re.fullmatch(r"\s*(`{3,}|~{3,})\s*", lines[last]):
        return "\n".join(lines[first + 1:last])
    return text


def _parse_edits(body: str) -> List[Edit]:
    edits = []
    pattern = re.compile(
        r"^\s*<{5,}\s*SEARCH\s*\n(.*?)\n?^\s*={5,}\s*\n(.*?)\n?^\s*>{5,}\s*REPLACE\s*$",
        re.DOTALL | re.MULTILINE,
    )
    for m in pattern.finditer(body):
        edits.append(Edit(search=m.group(1), replace=m.group(2)))
    return edits


def parse_file_blocks(text: str) -> ParsedOutput:
    lines = text.split("\n")
    blocks: List[FileBlock] = []
    current: Optional[FileBlock] = None
    buf: List[str] = []
    for line in lines:
        if current is None:
            m = _FILE_START.match(line)
            if m:
                current = FileBlock(path=clean_path(m.group(2)), kind=m.group(1).lower())
                buf = []
            continue
        if _FILE_END.match(line):
            _finish(current, buf, closed=True)
            blocks.append(current)
            current = None
            continue
        m = _FILE_START.match(line)
        if m:  # a new block started without closing the previous one
            _finish(current, buf, closed=True)
            blocks.append(current)
            current = FileBlock(path=clean_path(m.group(2)), kind=m.group(1).lower())
            buf = []
            continue
        buf.append(line)
    truncated = False
    if current is not None:
        _finish(current, buf, closed=False)
        blocks.append(current)
        truncated = True
    if not blocks:
        blocks = _parse_fenced_fallback(text)
    return ParsedOutput(blocks=blocks, truncated=truncated)


def _finish(block: FileBlock, buf: List[str], closed: bool) -> None:
    body = "\n".join(buf)
    block.closed = closed
    if block.kind == "edit":
        block.edits = _parse_edits(body)
    else:
        content = _strip_wrapping_fence(body).strip("\n")
        block.content = content + "\n"


_PATHLIKE = r"[A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]{1,8}"
_HEADER_PATH = re.compile(
    r"^\s*(?:#{1,6}\s*|\*\*|__)?\s*(?:file(?:name)?\s*[:：]\s*|파일\s*[:：]\s*)?`?(" + _PATHLIKE + r")`?\s*(?:\*\*|__)?\s*:?\s*$",
    re.IGNORECASE,
)
_INFO_PATH = re.compile(r"(?:^|[\s:])(?:title|file|filename|path)?=?\"?(" + _PATHLIKE + r")\"?\s*$", re.IGNORECASE)


def _parse_fenced_fallback(text: str) -> List[FileBlock]:
    """Fallback: '### index.html' (or 'File: index.html') followed by a ``` block, or ```html:index.html."""
    lines = text.split("\n")
    blocks: List[FileBlock] = []
    i = 0
    pending_path: Optional[str] = None
    while i < len(lines):
        line = lines[i]
        fm = _FENCE.match(line)
        if fm:
            fence, info = fm.group(1), fm.group(2).strip()
            path = None
            im = _INFO_PATH.search(info.replace(":", " ")) if info else None
            if im and "." in im.group(1):
                path = im.group(1)
            path = path or pending_path
            j = i + 1
            body = []
            while j < len(lines) and not lines[j].strip().startswith(fence[0] * len(fence)):
                body.append(lines[j])
                j += 1
            closed = j < len(lines)
            if path:
                blocks.append(FileBlock(path=clean_path(path), kind="file", content="\n".join(body).strip("\n") + "\n", closed=closed))
            pending_path = None
            i = j + 1
            continue
        hm = _HEADER_PATH.match(line)
        if hm:
            pending_path = hm.group(1)
        elif line.strip():
            pending_path = None
        i += 1
    return blocks


# --------------------------------------------------------------- apply edits

def apply_edits(original: str, edits: List[Edit]) -> Tuple[str, List[str]]:
    """Apply SEARCH/REPLACE edits. Returns (new_text, list_of_failed_search_snippets)."""
    text = original
    failed = []
    for e in edits:
        if e.search and e.search in text:
            text = text.replace(e.search, e.replace, 1)
            continue
        new = _fuzzy_replace(text, e.search, e.replace)
        if new is None:
            failed.append(e.search[:200])
        else:
            text = new
    return text, failed


def _fuzzy_replace(text: str, search: str, replace: str) -> Optional[str]:
    """Match ignoring trailing whitespace, then ignoring indentation, line by line."""
    s_lines = [l for l in search.split("\n")]
    while s_lines and not s_lines[0].strip():
        s_lines.pop(0)
    while s_lines and not s_lines[-1].strip():
        s_lines.pop()
    if not s_lines:
        return None
    t_lines = text.split("\n")
    for norm in (lambda l: l.rstrip(), lambda l: l.strip()):
        target = [norm(l) for l in s_lines]
        n = len(target)
        for i in range(len(t_lines) - n + 1):
            if [norm(l) for l in t_lines[i:i + n]] == target:
                return "\n".join(t_lines[:i] + replace.split("\n") + t_lines[i + n:])
    return None


# ------------------------------------------------------------------ sections

_HEADING = re.compile(r"^\s*#{1,3}\s+(.+?)\s*#*\s*$")


def split_sections(text: str) -> Dict[str, str]:
    """Map lower-cased '##' headings to their content. Repeated headings keep the last one."""
    sections: Dict[str, str] = {}
    current = None
    buf: List[str] = []
    for line in text.split("\n"):
        m = _HEADING.match(line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1).strip().strip("*").strip().lower()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def get_section(text: str, *names: str) -> str:
    secs = split_sections(text)
    for name in names:
        name = name.lower()
        for key, value in secs.items():
            if key == name or key.startswith(name):
                return value
    return ""


_ITEM = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+(.*\S)\s*$")


def list_items(section_text: str) -> List[str]:
    items: List[str] = []
    for line in section_text.split("\n"):
        m = _ITEM.match(line)
        if m:
            items.append(m.group(1).strip())
        elif items and line.startswith(("  ", "\t")) and line.strip():
            items[-1] += " " + line.strip()
    return items


def is_none(item: str) -> bool:
    return item.strip().strip(".*()").lower() in ("none", "n/a", "na", "없음", "없습니다", "-", "")


# ------------------------------------------------------------------- verdict

_VERDICT = re.compile(r"VERDICT\s*[:：]?\s*\**\s*(PASS|FAIL)", re.IGNORECASE)


def parse_verdict(text: str) -> Optional[str]:
    found = _VERDICT.findall(text)
    return found[-1].upper() if found else None


_ISSUE = re.compile(r"^\s*[-*•]?\s*\[\s*(critical|major|minor|high|medium|low)\s*\]\s*(.+)$", re.IGNORECASE)
_SEV_MAP = {"high": "major", "medium": "minor", "low": "minor"}


@dataclass
class Issue:
    severity: str
    text: str

    def __str__(self) -> str:
        return "[%s] %s" % (self.severity, self.text)


def parse_issues(text: str) -> List[Issue]:
    body = get_section(text, "issues") or text
    issues = []
    for line in body.split("\n"):
        m = _ISSUE.match(line)
        if m:
            sev = m.group(1).lower()
            issues.append(Issue(_SEV_MAP.get(sev, sev), m.group(2).strip()))
        elif issues and line.startswith(("  ", "\t")) and line.strip():
            issues[-1].text += " " + line.strip()
    return issues


def failed_criteria(text: str) -> List[str]:
    body = get_section(text, "criteria")
    return [i for i in list_items(body) if re.match(r"^\**\s*FAIL\b", i, re.IGNORECASE)]


# --------------------------------------------------------------------- steps

@dataclass
class Step:
    number: int
    title: str
    files: List[str]
    text: str


_STEP_HEAD = re.compile(r"^\s*#{2,4}\s*(?:Step|단계)\s*(\d+)\s*[:.)\-–]?\s*(.*)$", re.IGNORECASE)
_FILES_LINE = re.compile(r"^\s*[-*]?\s*\**(?:Files?|파일)\**\s*[:：]\s*(.+)$", re.IGNORECASE)


def _split_files(value: str) -> List[str]:
    out = []
    for part in re.split(r"[,;]|\s+and\s+", value):
        p = clean_path(part.split(" (")[0].split(" — ")[0].split(" - ")[0])
        if p and not is_none(p):
            out.append(p)
    return out


def parse_steps(plan: str) -> List[Step]:
    lines = plan.split("\n")
    steps: List[Step] = []
    current: Optional[Step] = None
    buf: List[str] = []

    def close():
        if current is not None:
            current.text = "\n".join(buf).strip()
            steps.append(current)

    for line in lines:
        m = _STEP_HEAD.match(line)
        if m:
            close()
            current = Step(int(m.group(1)), m.group(2).strip(), [], "")
            buf = [line.strip()]
            continue
        if current is not None:
            if re.match(r"^\s*##\s+\S", line) and not _STEP_HEAD.match(line):
                close()
                current = None
                continue
            fm = _FILES_LINE.match(line)
            if fm and not current.files:
                current.files = _split_files(fm.group(1))
            buf.append(line)
    close()
    if steps:
        return steps
    # Fallback: numbered items in the "Steps" section.
    body = get_section(plan, "steps")
    for n, item in enumerate(list_items(body), 1):
        files = []
        fm = re.search(r"\[files?\s*:\s*([^\]]+)\]", item, re.IGNORECASE)
        if fm:
            files = _split_files(fm.group(1))
        steps.append(Step(n, item[:80], files, "Step %d: %s" % (n, item)))
    return steps


def plan_files(plan: str) -> List[str]:
    items = list_items(get_section(plan, "files"))
    out = []
    for it in items:
        p = clean_path(re.split(r"\s+[—–-]\s+|\s+\(|:\s", it)[0])
        if "." in p or "/" in p:
            out.append(p)
    return out
