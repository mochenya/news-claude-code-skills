from __future__ import annotations

import argparse
import sys

try:
    import feedparser
except ImportError:
    print("Error: feedparser library not found. Install with: uv sync", file=sys.stderr)
    sys.exit(1)

from lib.db import (
    connect_db,
    current_timestamp,
    get_feed_rows_for_sync,
    init_db,
    sync_registry,
    update_feed_fetch_status,
    upsert_entry,
)
from lib.entry_utils import build_entry_payload
from lib.network import configure_network_timeout
from lib.source_registry import build_category_lookup, list_category_keys, load_source_registry

configure_network_timeout()


def parse_feed_with_metadata(feed_row):
    kwargs = {}
    if feed_row["etag"]:
        kwargs["etag"] = feed_row["etag"]
    if feed_row["modified"]:
        kwargs["modified"] = feed_row["modified"]
    return feedparser.parse(feed_row["feed_url"], **kwargs)


def sync_category(category_key: str | None = None) -> int:
    categories = load_source_registry()
    category_lookup = build_category_lookup(categories)
    if category_key and category_key not in category_lookup:
        print(f"Error: Unknown category '{category_key}'", file=sys.stderr)
        print(f"Available categories: {', '.join(list_category_keys(categories))}", file=sys.stderr)
        return 1

    conn = connect_db()
    init_db(conn)
    sync_registry(conn, categories)

    feed_rows = get_feed_rows_for_sync(conn, category_key)
    inserted = 0
    updated = 0
    unchanged = 0
    failed = 0
    scope = category_key or "all"

    print(f"Sync start: scope={scope} feeds={len(feed_rows)}")

    for index, feed_row in enumerate(feed_rows, start=1):
        checked_at = current_timestamp()
        feed_url = feed_row["feed_url"]
        print(f"[{index}/{len(feed_rows)}] Fetching {feed_url}")

        feed_inserted = 0
        feed_updated = 0
        feed_unchanged = 0

        try:
            feed = parse_feed_with_metadata(feed_row)
            if feed.bozo and not feed.entries:
                failed += 1
                error_text = str(getattr(feed, "bozo_exception", "failed to parse feed"))
                update_feed_fetch_status(
                    conn,
                    int(feed_row["id"]),
                    last_checked_at=checked_at,
                    last_status="error",
                    last_error=error_text,
                )
                conn.commit()
                print(f"  -> error: {error_text}")
                continue

            for entry in feed.entries:
                payload = build_entry_payload(entry, int(feed_row["id"]), checked_at)
                status = upsert_entry(conn, payload)
                if status == "inserted":
                    inserted += 1
                    feed_inserted += 1
                elif status == "updated":
                    updated += 1
                    feed_updated += 1
                else:
                    unchanged += 1
                    feed_unchanged += 1

            update_feed_fetch_status(
                conn,
                int(feed_row["id"]),
                last_checked_at=checked_at,
                feed_title=feed.feed.get("title"),
                site_url=feed.feed.get("link"),
                etag=getattr(feed, "etag", None),
                modified=str(getattr(feed, "modified", "") or "") or None,
                last_success_at=checked_at,
                last_status="ok",
                last_error=None,
            )
            conn.commit()
            print(
                "  -> ok: "
                f"entries={len(feed.entries)} inserted={feed_inserted} updated={feed_updated} unchanged={feed_unchanged}"
            )
        except Exception as exc:
            failed += 1
            update_feed_fetch_status(
                conn,
                int(feed_row["id"]),
                last_checked_at=checked_at,
                last_status="error",
                last_error=str(exc),
            )
            conn.commit()
            print(f"  -> error: {exc}")

    print(
        "Sync complete: "
        f"scope={scope} feeds={len(feed_rows)} inserted={inserted} updated={updated} "
        f"unchanged={unchanged} failed={failed}"
    )
    return 0 if failed == 0 else 2


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    parser = argparse.ArgumentParser(prog=prog, description="Sync RSS feeds into sqlite storage")
    parser.add_argument("category", nargs="?", help="Category key to sync")
    parser.add_argument("--all", action="store_true", help="Sync all categories")
    args = parser.parse_args(argv)

    if args.all:
        return sync_category(None)
    if not args.category:
        parser.print_help(file=sys.stderr)
        print("\nError: Please specify a category or use --all", file=sys.stderr)
        return 1
    return sync_category(args.category)


if __name__ == "__main__":
    sys.exit(main())
