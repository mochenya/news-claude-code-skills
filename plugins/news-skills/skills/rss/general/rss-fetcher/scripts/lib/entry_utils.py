from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .text_utils import clean_html
from .time_utils import extract_entry_timestamp, format_timestamp_to_bjt_iso

STRING_TIME_FIELDS = (
    "published",
    "updated",
    "created",
    "pubDate",
    "date",
    "issued",
    "modified",
)

IDENTIFIER_FIELDS = ("id", "guid")
AUTHOR_FIELDS = ("author", "authors")


def build_entry_payload(entry: Mapping[str, Any], feed_id: int, fetched_at: int) -> dict[str, object]:
    title = clean_html(_as_text(entry.get("title", "")))
    link = _as_text(entry.get("link", "")).strip()
    description_raw = _as_text(entry.get("description", "") or entry.get("summary", ""))
    description_text = clean_html(description_raw)
    published_ts = extract_entry_timestamp(entry)
    published_iso_bjt = format_timestamp_to_bjt_iso(published_ts)
    raw_published = _extract_raw_published(entry)
    guid_raw = _extract_guid(entry)
    author = _extract_author(entry)
    entry_key = build_entry_key(entry, link=link, title=title, raw_published=raw_published)
    content_hash = build_content_hash(
        title=title,
        link=link,
        description_text=description_text,
        published_iso_bjt=published_iso_bjt,
        author=author,
    )
    return {
        "feed_id": feed_id,
        "entry_key": entry_key,
        "guid_raw": guid_raw or None,
        "link": link or None,
        "title": title,
        "description_text": description_text,
        "author": author or None,
        "published_ts": published_ts,
        "published_iso_bjt": published_iso_bjt or None,
        "raw_published": raw_published or None,
        "content_hash": content_hash,
        "fetched_at": fetched_at,
    }


def build_entry_key(
    entry: Mapping[str, Any],
    *,
    link: str,
    title: str,
    raw_published: str,
) -> str:
    guid_raw = _extract_guid(entry)
    if guid_raw:
        return f"guid:{guid_raw.strip()}"
    if link:
        return f"link:{link}"
    basis = json.dumps(
        {
            "title": title,
            "raw_published": raw_published,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return "hash:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()


def build_content_hash(*, title: str, link: str, description_text: str, published_iso_bjt: str, author: str) -> str:
    basis = json.dumps(
        {
            "title": title,
            "link": link,
            "description_text": description_text,
            "published": published_iso_bjt,
            "author": author,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _extract_raw_published(entry: Mapping[str, Any]) -> str:
    for field in STRING_TIME_FIELDS:
        value = entry.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_guid(entry: Mapping[str, Any]) -> str:
    for field in IDENTIFIER_FIELDS:
        value = entry.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_author(entry: Mapping[str, Any]) -> str:
    value = entry.get("author")
    if isinstance(value, str) and value.strip():
        return value.strip()

    authors = entry.get("authors")
    if isinstance(authors, list):
        names: list[str] = []
        for item in authors:
            if isinstance(item, dict):
                name = item.get("name")
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())
        if names:
            return ", ".join(names)
    return ""


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else ""
