"""Console safety — the one place that makes text cp1252-safe.

Windows consoles (cp1252) crash on characters they cannot encode (arrows,
emoji, some math symbols). Every runtime formatter folds text to cp1252,
keeping Spanish accents and replacing the truly-unencodable with '?'.

All formatters import this single helper instead of re-implementing it.
"""
from __future__ import annotations


def safe(text: str) -> str:
    """Fold text to what a cp1252 console can print (never raises)."""
    try:
        return text.encode("cp1252", errors="replace").decode("cp1252")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text.encode("ascii", errors="replace").decode("ascii")
