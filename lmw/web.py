"""Web search and page reading for the agent (standard library only).

Search engines, in order:
  1. SearXNG, if "search_url" is set in the config (e.g. "http://localhost:8080") — private, no limits
  2. Brave Search API, if the environment variable BRAVE_API_KEY is set
  3. DuckDuckGo's HTML page, then Bing (no key needed)
"""

from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from . import __version__

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36 lmw/" + __version__)


def _get(url: str, timeout: float = 15, headers: Optional[Dict[str, str]] = None, data: Optional[bytes] = None) -> str:
    h = {"User-Agent": UA, "Accept-Language": "ko,en;q=0.8"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(3_000_000)
        charset = r.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def _searxng(base: str, query: str, n: int) -> List[Dict[str, str]]:
    url = base.rstrip("/") + "/search?" + urllib.parse.urlencode({"q": query, "format": "json"})
    d = json.loads(_get(url))
    return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in d.get("results", [])[:n]]


def _brave(key: str, query: str, n: int) -> List[Dict[str, str]]:
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": n})
    d = json.loads(_get(url, headers={"Accept": "application/json", "X-Subscription-Token": key}))
    return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": _clean(r.get("description", ""))}
            for r in (d.get("web") or {}).get("results", [])[:n]]


def _duckduckgo(query: str, n: int) -> List[Dict[str, str]]:
    page = _get("https://html.duckduckgo.com/html/", data=urllib.parse.urlencode({"q": query, "kl": "kr-kr"}).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"})
    out = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="result__a"|$)',
                         page, re.S):
        href, title, rest = m.group(1), m.group(2), m.group(3)
        if "uddg=" in href:  # DuckDuckGo redirect link -> real URL
            href = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0])
        if href.startswith("//"):
            href = "https:" + href
        if "duckduckgo.com/y.js" in href:  # ads
            continue
        sn = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', rest, re.S)
        out.append({"title": _clean(title), "url": href, "snippet": _clean(sn.group(1)) if sn else ""})
        if len(out) >= n:
            break
    return out


def _bing(query: str, n: int) -> List[Dict[str, str]]:
    import base64
    page = _get("https://www.bing.com/search?" + urllib.parse.urlencode({"q": query, "setlang": "ko", "count": n}))
    out = []
    for block in re.findall(r'<li class="b_algo"(.*?)</li>', page, re.S):
        a = re.search(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not a:
            continue
        href = html.unescape(a.group(1))
        if "bing.com/ck/a" in href:  # redirect link: the real URL is base64 in u=a1...
            u = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("u", [""])[0]
            if u.startswith("a1"):
                try:
                    href = base64.urlsafe_b64decode(u[2:] + "=" * (-len(u[2:]) % 4)).decode("utf-8", "replace")
                except ValueError:
                    pass
        sn = re.search(r'<p[^>]*>(.*?)</p>', block, re.S)
        out.append({"title": _clean(a.group(2)), "url": href, "snippet": _clean(sn.group(1)) if sn else ""})
        if len(out) >= n:
            break
    return out


def search(query: str, n: int = 8, searxng: str = "") -> List[Dict[str, str]]:
    n = max(1, min(int(n or 8), 15))
    errors = []
    engines = []
    if searxng or os.environ.get("LMW_SEARXNG"):
        engines.append(lambda: _searxng(searxng or os.environ["LMW_SEARXNG"], query, n))
    if os.environ.get("BRAVE_API_KEY"):
        engines.append(lambda: _brave(os.environ["BRAVE_API_KEY"], query, n))
    engines.append(lambda: _duckduckgo(query, n))
    engines.append(lambda: _bing(query, n))  # DuckDuckGo sometimes shows a bot check instead of results
    for engine in engines:
        try:
            res = [r for r in engine() if r.get("url")]
            if res:
                return res
        except Exception as e:  # try the next engine
            errors.append(str(e))
    if errors:
        raise OSError("검색 실패: " + "; ".join(errors[-2:]))
    return []


def fetch_text(url: str, limit: int = 12000) -> Dict[str, str]:
    """Download a page and return its readable text (scripts, styles and navigation removed)."""
    if not re.match(r"https?://", url):
        url = "https://" + url
    page = _get(url, timeout=20)
    title = _clean((re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I) or [None, ""])[1])
    body = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|form|iframe)[^>]*>.*?</\1>", " ", page)
    body = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|section|article)>", "\n", body)
    body = re.sub(r"(?i)<li[^>]*>", "\n- ", body)
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    lines = [re.sub(r"[ \t ]+", " ", l).strip() for l in text.splitlines()]
    text = "\n".join(l for l in lines if len(l) > 1)
    text = re.sub(r"\n{3,}", "\n\n", text)
    more = len(text) > limit
    return {"url": url, "title": title, "text": text[:limit] + ("\n… (잘림)" if more else "")}
