from __future__ import annotations

import re
from html import unescape


def strip_html(text: str) -> str:
    """Remove HTML tags, keep text."""
    return re.sub(r"<[^>]+>", "", text or "")


def clean_html(text: str) -> str:
    """Remove HTML tags and unescape entities, collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()
