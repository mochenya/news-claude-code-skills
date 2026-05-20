from __future__ import annotations

import argparse
import json
import sys

from lib.db import connect_db, get_category_query_rows, get_category_rows, init_db, sync_registry
from lib.source_registry import load_source_registry
from lib.time_utils import format_timestamp_to_bjt_iso, resolve_query_time_range

# 展示查询时候不需要限制
# TRUNCATE_TEXT_LIMIT = 200


def format_story_text(index: int, row) -> str:
    lines = [f"{index}. [{row['source_name']}] {row['title']}"]
    description = (row["description_text"] or "").strip()
    # if description:
    #     if len(description) > TRUNCATE_TEXT_LIMIT:
    #         description = description[: TRUNCATE_TEXT_LIMIT - 3] + "..."
    lines.append(f"content:\n```\n{description}\n```")
    if row["link"]:
        lines.append(f"Link: {row['link']}")
    if row["published_iso_bjt"]:
        lines.append(f"Date: {row['published_iso_bjt']}")
    lines.append("")
    return "\n".join(lines)


def build_time_range_payload(since_ts: int | None, until_ts: int | None) -> dict[str, str | None]:
    return {
        "since": format_timestamp_to_bjt_iso(since_ts) or None,
        "until": format_timestamp_to_bjt_iso(until_ts) or None,
    }


def print_time_range_header(since_ts: int | None, until_ts: int | None) -> None:
    if since_ts is None and until_ts is None:
        return
    since_text = format_timestamp_to_bjt_iso(since_ts) or "-inf"
    until_text = format_timestamp_to_bjt_iso(until_ts) or "+inf"
    print(f"Time Range: [{since_text}, {until_text})")
    print()


def connect_query_db():
    conn = connect_db()
    init_db(conn)
    sync_registry(conn, load_source_registry())
    return conn


def query_category_text(
    category_key: str,
    *,
    limit: int | None = None,
    since_ts: int | None = None,
    until_ts: int | None = None,
) -> int:
    conn = connect_query_db()
    category, rows = get_category_query_rows(conn, category_key, limit=limit, since_ts=since_ts, until_ts=until_ts)
    if category is None:
        print(f"Error: Unknown category '{category_key}'", file=sys.stderr)
        return 1

    print(f"Category: {category['category_key']} - {category['category_name']}")
    print_time_range_header(since_ts, until_ts)
    print("=" * 60)
    print()
    if not rows:
        print("No items found.")
        return 0
    for index, row in enumerate(rows, start=1):
        print(format_story_text(index, row))
    return 0


def query_category_json(
    category_key: str,
    *,
    limit: int | None = None,
    since_ts: int | None = None,
    until_ts: int | None = None,
) -> int:
    conn = connect_query_db()
    category, rows = get_category_query_rows(conn, category_key, limit=limit, since_ts=since_ts, until_ts=until_ts)
    if category is None:
        print(f"Error: Unknown category '{category_key}'", file=sys.stderr)
        return 1
    payload = {
        "time_range": build_time_range_payload(since_ts, until_ts),
        "items": [
            {
                "source": row["source_name"],
                "title": row["title"],
                "link": row["link"],
                "description": row["description_text"],
                "published": row["published_iso_bjt"] or "",
            }
            for row in rows
        ],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def query_all_text(*, limit: int | None = None, since_ts: int | None = None, until_ts: int | None = None) -> int:
    conn = connect_query_db()
    categories = get_category_rows(conn)
    for idx, category in enumerate(categories):
        if idx:
            print()
        _, rows = get_category_query_rows(
            conn,
            category["category_key"],
            limit=limit,
            since_ts=since_ts,
            until_ts=until_ts,
        )
        print(f"Category: {category['category_key']} - {category['category_name']}")
        print_time_range_header(since_ts, until_ts)
        print("=" * 60)
        print()
        if not rows:
            print("No items found.")
            continue
        for item_index, row in enumerate(rows, start=1):
            print(format_story_text(item_index, row))
    return 0


def query_all_json(*, limit: int | None = None, since_ts: int | None = None, until_ts: int | None = None) -> int:
    conn = connect_query_db()
    categories = get_category_rows(conn)
    payload = {
        "time_range": build_time_range_payload(since_ts, until_ts),
        "categories": [],
    }
    for category in categories:
        _, rows = get_category_query_rows(
            conn,
            category["category_key"],
            limit=limit,
            since_ts=since_ts,
            until_ts=until_ts,
        )
        payload["categories"].append(
            {
                "category": category["category_key"],
                "items": [
                    {
                        "source": row["source_name"],
                        "title": row["title"],
                        "link": row["link"],
                        "description": row["description_text"],
                        "published": row["published_iso_bjt"] or "",
                    }
                    for row in rows
                ],
            }
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def list_categories() -> int:
    categories = load_source_registry()
    print("\nAvailable Categories:")
    print("=" * 60)
    for category in categories:
        if not category.enabled:
            continue
        print(f"\n{category.key:15} - {category.name}")
        enabled_sources = [source for source in category.sources if source.enabled]
        print(f"{'':15}  Sources: {len(enabled_sources)}")
        for source in enabled_sources:
            print(f"{'':15}    • {source.name}")
    print()
    return 0


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    parser = argparse.ArgumentParser(prog=prog, description="Query RSS news from sqlite storage")
    parser.add_argument("category", nargs="?", help="Category key to query")
    parser.add_argument("-l", "--limit", type=int, default=None, help="Limit number of items per category")
    parser.add_argument("-f", "--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--since", help="Lower time bound, recommended: ISO 8601 with timezone")
    parser.add_argument("--until", help="Upper time bound, recommended: ISO 8601 with timezone")
    parser.add_argument("--list", action="store_true", help="List categories")
    parser.add_argument("--all", action="store_true", help="Query all categories")
    args = parser.parse_args(argv)

    try:
        since_ts, until_ts = resolve_query_time_range(args.since, args.until)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.list:
        return list_categories()
    if args.all:
        return (
            query_all_json(limit=args.limit, since_ts=since_ts, until_ts=until_ts)
            if args.format == "json"
            else query_all_text(limit=args.limit, since_ts=since_ts, until_ts=until_ts)
        )
    if not args.category:
        parser.print_help(file=sys.stderr)
        print("\nError: Please specify a category or use --list", file=sys.stderr)
        return 1
    return (
        query_category_json(args.category, limit=args.limit, since_ts=since_ts, until_ts=until_ts)
        if args.format == "json"
        else query_category_text(args.category, limit=args.limit, since_ts=since_ts, until_ts=until_ts)
    )


if __name__ == "__main__":
    sys.exit(main())
