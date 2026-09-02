"""jp-kr-news CLI — fetch Japan/Korea politics & economy RSS feeds."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import feedparser
except ImportError:
    print("Error: feedparser not found. Run: uv sync", file=sys.stderr)
    sys.exit(1)

from lib.text_utils import clean_html
from lib.time_utils import extract_entry_bjt_fields

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SOURCES_PATH = DATA_DIR / "sources.json"
BJT = timezone(timedelta(hours=8))


# ---------------------------------------------------------------------------
# Source registry (inline, no DB)
# ---------------------------------------------------------------------------

def load_sources(path: Path | None = None) -> list[dict[str, Any]]:
    """Load enabled sources from sources.json, return [{key, name, url}, ...]."""
    p = path or SOURCES_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    sources: list[dict[str, Any]] = []
    for cat in data.get("categories", []):
        if not cat.get("enabled", True):
            continue
        for src in cat.get("sources", []):
            if not src.get("enabled", True):
                continue
            sources.append({
                "key": src["key"],
                "name": src["name"],
                "url": src["url"],
            })
    return sources


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _fetch_one(source: dict[str, Any], limit: int | None) -> list[dict[str, Any]]:
    """Fetch one RSS source, return list of entry dicts."""
    feed = feedparser.parse(source["url"])
    if feed.bozo and not feed.entries:
        print(
            f"[{source['name']}] error: {getattr(feed, 'bozo_exception', 'parse failed')}",
            file=sys.stderr,
        )
        return []

    entries: list[dict[str, Any]] = []
    for entry in feed.entries[:limit]:
        published_bjt, _ = extract_entry_bjt_fields(entry)
        desc = entry.get("description", "") or entry.get("summary", "")
        entries.append({
            "source_name": source["name"],
            "source_key": source["key"],
            "title": entry.title,
            "link": entry.link,
            "description": clean_html(desc),
            "published_bjt": published_bjt,
        })
    return entries


def _dedup_by_link(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove exact link duplicates, keep first occurrence."""
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for e in entries:
        link = e["link"]
        if link in seen:
            continue
        seen.add(link)
        result.append(e)
    return result


def _sort_by_time(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort newest first by published_bjt."""
    return sorted(entries, key=lambda e: e.get("published_bjt", ""), reverse=True)


def _parse_iso8601(value: str) -> datetime:
    """Parse an ISO 8601 timestamp and normalize it to Beijing time."""
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BJT)
    return parsed.astimezone(BJT)


def _filter_by_time_window(
    entries: list[dict[str, Any]],
    since: str | None = None,
    until: str | None = None,
) -> list[dict[str, Any]]:
    """Keep entries in the half-open interval [since, until)."""
    since_dt = _parse_iso8601(since) if since else None
    until_dt = _parse_iso8601(until) if until else None
    if since_dt and until_dt and since_dt >= until_dt:
        raise ValueError("--since must be earlier than --until")
    if not since_dt and not until_dt:
        return entries

    result: list[dict[str, Any]] = []
    for entry in entries:
        published = entry.get("published_bjt")
        if not published:
            continue
        try:
            published_dt = _parse_iso8601(published)
        except (TypeError, ValueError):
            continue
        if since_dt and published_dt < since_dt:
            continue
        if until_dt and published_dt >= until_dt:
            continue
        result.append(entry)
    return result


def _format_text(entries: list[dict[str, Any]]) -> str:
    """Format entries as text output, chronological order with source prefix."""
    lines: list[str] = []
    for i, e in enumerate(entries, 1):
        lines.append(f"\n{i}. [{e['source_name']}] {e['title']}")
        if e["description"]:
            desc = e["description"][:300]
            lines.append(f"   {desc}")
        lines.append(f"   Link: {e['link']}")
        if e["published_bjt"]:
            lines.append(f"   Date: {e['published_bjt']}")
    return "\n".join(lines).strip()


def cmd_fetch(args: argparse.Namespace) -> int:
    """Fetch RSS sources and print merged text."""
    sources = load_sources()

    if args.source:
        sources = [s for s in sources if s["key"] == args.source]
        if not sources:
            print(f"Unknown source: {args.source}", file=sys.stderr)
            keys = [s["key"] for s in load_sources()]
            print(f"Available: {', '.join(keys)}", file=sys.stderr)
            return 1

    limit = args.limit

    all_entries: list[dict[str, Any]] = []
    for src in sources:
        print(f"[{src['name']}] fetching...", file=sys.stderr)
        entries = _fetch_one(src, limit)
        print(f"  -> {len(entries)} items", file=sys.stderr)
        all_entries.extend(entries)

    # dedup by link
    all_entries = _dedup_by_link(all_entries)
    # strict half-open time window [since, until)
    try:
        all_entries = _filter_by_time_window(
            all_entries,
            since=args.since,
            until=args.until,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    # sort
    all_entries = _sort_by_time(all_entries)

    if args.format == "json":
        print(json.dumps(all_entries, indent=2, ensure_ascii=False))
    else:
        print(f"\n# JP-KR News · {len(all_entries)} items · {len(sources)} sources")
        print(_format_text(all_entries))
        print(f"\n---\nTotal: {len(all_entries)} items from {len(sources)} sources")

    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    """List available sources."""
    sources = load_sources()
    print(f"{'KEY':<30} {'NAME':<30} URL")
    print("-" * 90)
    for s in sources:
        print(f"{s['key']:<30} {s['name']:<30} {s['url']}")
    print(f"\n{len(sources)} sources")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jpkr",
        description="Japan-Korea politics & economy RSS news toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  jpkr fetch --all --since '2026-07-16T08:00:00+08:00' "
            "--until '2026-07-16T12:00:00+08:00' -f json\n"
            "  jpkr list                     List sources\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    # fetch
    fetch_p = sub.add_parser("fetch", help="Fetch RSS feeds")
    fetch_p.add_argument("--all", action="store_true", help="Fetch all sources")
    fetch_p.add_argument("--source", type=str, help="Fetch single source by key")
    fetch_p.add_argument("-l", "--limit", type=int, default=None, help="Optional per-source cap; default scans the full feed")
    fetch_p.add_argument("--since", required=True, help="Window start in ISO 8601; inclusive")
    fetch_p.add_argument("--until", required=True, help="Window end in ISO 8601; exclusive")
    fetch_p.add_argument("-f", "--format", choices=["text", "json"], default="text", help="Output format")

    # list
    sub.add_parser("list", help="List available sources")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "fetch":
        if not args.all and not args.source:
            parser.error("fetch requires --all or --source <key>")
        return cmd_fetch(args)
    elif args.command == "list":
        return cmd_list(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
