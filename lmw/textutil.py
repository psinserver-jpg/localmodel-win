"""Small text helpers: token estimation, budget-aware truncation, language detection."""

from __future__ import annotations

import re


def estimate_tokens(text: str) -> int:
    """Conservative token estimate without a tokenizer.

    ASCII text averages ~3.5-4 chars/token; CJK/Hangul is often ~1 token per char.
    Overestimating is safer than overflowing the context window.
    """
    if not text:
        return 0
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    other = len(text) - ascii_chars
    return int(ascii_chars / 3.3 + other * 1.1) + 1


def truncate_to_tokens(text: str, max_tokens: int, note: str = "[... truncated to fit the context window ...]") -> str:
    if estimate_tokens(text) <= max_tokens:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if estimate_tokens(text[:mid]) <= max_tokens - 20:
            lo = mid
        else:
            hi = mid - 1
    cut = text[:lo]
    nl = cut.rfind("\n")
    if nl > lo * 0.7:
        cut = cut[:nl]
    return cut + "\n" + note


def tail_tokens(text: str, max_tokens: int) -> str:
    """Return the END of `text`, trimmed to about `max_tokens`."""
    if estimate_tokens(text) <= max_tokens:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        if estimate_tokens(text[mid:]) <= max_tokens:
            hi = mid
        else:
            lo = mid + 1
    return text[lo:]


_HANGUL = re.compile(r"[가-힣]")
_KANA = re.compile(r"[぀-ヿ]")
_HAN = re.compile(r"[一-鿿]")


def detect_language(text: str) -> str:
    if _HANGUL.search(text):
        return "Korean"
    if _KANA.search(text):
        return "Japanese"
    if _HAN.search(text):
        return "Chinese"
    return "English"


_LANG_NAMES = {"ko": "Korean", "ja": "Japanese", "zh": "Chinese", "en": "English", "es": "Spanish", "fr": "French",
               "de": "German", "pt": "Portuguese", "ru": "Russian", "it": "Italian", "vi": "Vietnamese", "th": "Thai",
               "id": "Indonesian", "tr": "Turkish", "ar": "Arabic", "hi": "Hindi"}
_WIN_LANGID = {0x12: "Korean", 0x11: "Japanese", 0x04: "Chinese", 0x09: "English", 0x0a: "Spanish", 0x0c: "French",
               0x07: "German", 0x16: "Portuguese", 0x19: "Russian", 0x10: "Italian"}


def _name_for(code: str) -> str:
    """'ko', 'ko_KR.UTF-8', 'Korean', 'korean' -> 'Korean' (unknown names are passed through)."""
    c = (code or "").strip()
    if not c:
        return ""
    base = c.replace("-", "_").split("_")[0].split(".")[0].lower()
    if base in _LANG_NAMES:
        return _LANG_NAMES[base]
    for name in _LANG_NAMES.values():
        if c.lower() == name.lower():
            return name
    return c[:1].upper() + c[1:]


def system_language() -> str:
    """The computer's language (LMW_LANG, else the OS UI language); English if unknown."""
    import os
    env = os.environ.get("LMW_LANG", "").strip()
    if env:
        return _name_for(env)
    try:
        import sys
        if sys.platform == "win32":
            import ctypes
            lid = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3ff
            if lid in _WIN_LANGID:
                return _WIN_LANGID[lid]
        elif sys.platform == "darwin":
            import subprocess
            out = subprocess.run(["defaults", "read", "-g", "AppleLanguages"], capture_output=True, text=True,
                                 timeout=3).stdout
            m = re.search(r'"?([a-zA-Z]{2,3})(?:[-_][A-Za-z]+)*"?\s*[,)]', out)
            if m and _name_for(m.group(1)) in _LANG_NAMES.values():
                return _name_for(m.group(1))
    except Exception:
        pass
    import locale
    for getter in (lambda: locale.getlocale()[0], lambda: locale.getdefaultlocale()[0]):
        try:
            loc = getter()
        except Exception:
            loc = None
        if loc and loc.upper() not in ("C", "POSIX") and _name_for(loc) in _LANG_NAMES.values():
            return _name_for(loc)
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var, "")
        if v and _name_for(v) in _LANG_NAMES.values():
            return _name_for(v)
    return "English"


def preferred_language(text: str = "", setting: str = "auto") -> str:
    """Language for replies: the config's `language` if set, else the request's script (Hangul, kana, Han),
    else the computer's (system) language."""
    s = (setting or "auto").strip()
    if s.lower() != "auto":
        return _name_for(s)
    d = detect_language(text or "")
    return d if d != "English" else system_language()


def looks_like(text: str, lang: str) -> bool:
    """False when `text` is clearly not written in `lang` (only checked for Korean, Japanese and Chinese)."""
    script = {"Korean": _HANGUL, "Japanese": re.compile(r"[぀-ヿ一-鿿]"), "Chinese": _HAN}.get(lang)
    if script is None:
        return True
    prose = re.sub(r"```.*?```", " ", text, flags=re.S)
    prose = re.sub(r"`[^`]*`|https?://\S+|[\w./\\-]+\.\w{1,5}\b", " ", prose)
    letters = re.findall(r"[^\W\d_]", prose)
    if len(letters) < 40:
        return True
    return len(script.findall(prose)) / len(letters) >= 0.25


def language_rule(text: str, setting: str = "auto") -> str:
    lang = preferred_language(text, setting)
    return (
        "Write all explanations and all user-visible content (UI text, copy, messages) in %s, "
        "unless the request says otherwise. Keep section headings, VERDICT lines, FILE/EDIT markers, "
        "code, identifiers and file names exactly as specified (in English)." % lang
    )
