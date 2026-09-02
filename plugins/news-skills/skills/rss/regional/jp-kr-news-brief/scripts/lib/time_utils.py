from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping

BJT = timezone(timedelta(hours=8))
STRING_TIME_FIELDS = (
    "published",
    "updated",
    "created",
    "pubDate",
    "date",
    "issued",
    "modified",
)
PARSED_TIME_FIELDS = (
    "published_parsed",
    "updated_parsed",
    "created_parsed",
)
RELATIVE_TIME_RE = re.compile(r"^(?P<value>\d+)(?P<unit>[mhdw])$", re.IGNORECASE)


def _normalize_iso_datetime(value: str) -> str:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", normalized)
    return normalized


def parse_datetime_to_timestamp(
    value: str | None, *, default_tz: timezone = timezone.utc
) -> int | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None

    dt: datetime | None = None
    try:
        # Some RSS feeds use RFC 2822 dates with a colon in the numeric
        # timezone (e.g. ``+09:00``). ``parsedate_to_datetime`` accepts the
        # string but silently returns a naive datetime for that form, so
        # normalize the offset before parsing to preserve the source zone.
        rfc_text = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", text)
        dt = parsedate_to_datetime(rfc_text)
    except (TypeError, ValueError, IndexError, OverflowError):
        dt = None

    if dt is None:
        try:
            dt = datetime.fromisoformat(_normalize_iso_datetime(text))
        except ValueError:
            dt = None

    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return int(dt.timestamp())


def parse_struct_time_to_timestamp(value: Any) -> int | None:
    if not value:
        return None
    try:
        dt = datetime(*value[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    return int(dt.timestamp())


def extract_entry_timestamp(entry: Mapping[str, Any]) -> int | None:
    for field in STRING_TIME_FIELDS:
        timestamp = parse_datetime_to_timestamp(entry.get(field))
        if timestamp is not None:
            return timestamp
    for field in PARSED_TIME_FIELDS:
        timestamp = parse_struct_time_to_timestamp(entry.get(field))
        if timestamp is not None:
            return timestamp
    return None


def format_timestamp_to_bjt(timestamp: int | float | None) -> str:
    if timestamp is None:
        return ""
    dt = datetime.fromtimestamp(timestamp, tz=BJT)
    return dt.isoformat(timespec="seconds")


def extract_entry_bjt_fields(entry: Mapping[str, Any]) -> tuple[str, str]:
    timestamp = extract_entry_timestamp(entry)
    if timestamp is None:
        return "", ""
    bjt = format_timestamp_to_bjt(timestamp)
    return bjt, bjt


def parse_user_datetime_to_timestamp(
    value: str | None,
    *,
    now_ts: int | None = None,
    default_tz: timezone = BJT,
) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None

    relative_match = RELATIVE_TIME_RE.fullmatch(text)
    if relative_match:
        base_ts = int(
            now_ts if now_ts is not None else datetime.now(tz=default_tz).timestamp()
        )
        amount = int(relative_match.group("value"))
        unit = relative_match.group("unit").lower()
        seconds = {"m": 60, "h": 3600, "d": 86400, "w": 604800}[unit]
        return base_ts - amount * seconds

    normalized = text.replace("/", "-")
    return parse_datetime_to_timestamp(normalized, default_tz=default_tz)


def resolve_query_time_range(
    since_text: str | None,
    until_text: str | None,
    *,
    now_ts: int | None = None,
    default_tz: timezone = BJT,
) -> tuple[int | None, int | None]:
    since_ts = parse_user_datetime_to_timestamp(
        since_text, now_ts=now_ts, default_tz=default_tz
    )
    until_ts = parse_user_datetime_to_timestamp(
        until_text, now_ts=now_ts, default_tz=default_tz
    )
    if since_text and since_ts is None:
        raise ValueError(f"Invalid --since value: {since_text}")
    if until_text and until_ts is None:
        raise ValueError(f"Invalid --until value: {until_text}")
    if (
        since_ts is not None
        and until_ts is not None
        and since_ts >= until_ts
    ):
        raise ValueError(
            "Invalid time range: --since must be earlier than --until"
        )
    return since_ts, until_ts
