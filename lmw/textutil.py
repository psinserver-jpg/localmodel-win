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


def language_rule(text: str) -> str:
    lang = detect_language(text)
    return (
        "Write all explanations and all user-visible content (UI text, copy, messages) in %s, "
        "unless the request says otherwise. Keep section headings, VERDICT lines, FILE/EDIT markers, "
        "code, identifiers and file names exactly as specified (in English)." % lang
    )
