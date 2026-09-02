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
DATE_ONLY_RE = re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}$")
COMPACT_DATE_RE = re.compile(r"^\d{8}$")
COMPACT_DATETIME_RE = re.compile(r"^\d{12}(?:\d{2})?$")


def _normalize_iso_datetime(value: str) -> str:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", normalized)
    return normalized


def parse_datetime_to_timestamp(value: str | None, *, default_tz: timezone = timezone.utc) -> int | None:
    if not value:
        return None

    text = value.strip()
    if not text:
        return None

    dt: datetime | None = None

    try:
        dt = parsedate_to_datetime(text)
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


def format_timestamp_to_bjt_iso(timestamp: int | float | None) -> str:
    if timestamp is None:
        return ""
    dt = datetime.fromtimestamp(timestamp, tz=BJT)
    return dt.isoformat(timespec="seconds")


def extract_entry_bjt_fields(entry: Mapping[str, Any]) -> tuple[str, str]:
    timestamp = extract_entry_timestamp(entry)
    if timestamp is None:
        return "", ""
    return format_timestamp_to_bjt(timestamp), format_timestamp_to_bjt_iso(timestamp)


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
        base_ts = int(now_ts if now_ts is not None else datetime.now(tz=default_tz).timestamp())
        amount = int(relative_match.group("value"))
        unit = relative_match.group("unit").lower()
        seconds = {
            "m": 60,
            "h": 3600,
            "d": 86400,
            "w": 604800,
        }[unit]
        return base_ts - amount * seconds

    normalized = text.replace("/", "-")

    if COMPACT_DATE_RE.fullmatch(text):
        normalized = f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    elif COMPACT_DATETIME_RE.fullmatch(text):
        if len(text) == 12:
            normalized = (
                f"{text[0:4]}-{text[4:6]}-{text[6:8]} "
                f"{text[8:10]}:{text[10:12]}:00"
            )
        else:
            normalized = (
                f"{text[0:4]}-{text[4:6]}-{text[6:8]} "
                f"{text[8:10]}:{text[10:12]}:{text[12:14]}"
            )

    return parse_datetime_to_timestamp(normalized, default_tz=default_tz)


def resolve_query_time_range(
    since_text: str | None,
    until_text: str | None,
    *,
    now_ts: int | None = None,
    default_tz: timezone = BJT,
) -> tuple[int | None, int | None]:
    since_ts = parse_user_datetime_to_timestamp(since_text, now_ts=now_ts, default_tz=default_tz)
    until_ts = parse_user_datetime_to_timestamp(until_text, now_ts=now_ts, default_tz=default_tz)

    if since_text and since_ts is None:
        raise ValueError(f"Invalid --since value: {since_text}")
    if until_text and until_ts is None:
        raise ValueError(f"Invalid --until value: {until_text}")

    if since_ts is not None and until_ts is not None and since_ts >= until_ts:
        raise ValueError("Invalid time range: --since must be earlier than --until")

    return since_ts, until_ts


def is_date_only_input(value: str | None) -> bool:
    if value is None:
        return False
    text = value.strip()
    if not text:
        return False
    if DATE_ONLY_RE.fullmatch(text):
        return True
    if COMPACT_DATE_RE.fullmatch(text):
        return True
    return False
