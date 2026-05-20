from __future__ import annotations

import re
from html import unescape


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()
