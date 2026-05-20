"""Generic RSS Reader - Fetch and display news items from any RSS feed."""

from __future__ import annotations

import argparse
import json
import sys

try:
    import feedparser
except ImportError:
    print(
        "Error: feedparser library not found. Install with: uv sync",
        file=sys.stderr,
    )
    sys.exit(1)

from lib.network import configure_network_timeout
from lib.text_utils import strip_html
from lib.time_utils import extract_entry_bjt_fields

configure_network_timeout()


def fetch_rss(url: str, limit: int = 15, output_format: str = "text") -> int:
    """Fetch news items from any RSS feed"""
    feed = feedparser.parse(url)

    # Only treat bozo as an error if there are no entries (real failure)
    # Some feeds set bozo due to minor encoding warnings but still work fine
    if feed.bozo and not feed.entries:
        print(f"Error: Failed to parse feed from {url}", file=sys.stderr)
        if hasattr(feed, "bozo_exception"):
            print(f"  Reason: {feed.bozo_exception}", file=sys.stderr)
        return 1

    entries = feed.entries[:limit]

    if output_format == "json":
        stories = []
        for entry in entries:
            published_bjt, _published_iso = extract_entry_bjt_fields(entry)
            stories.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "description": entry.get("description", ""),
                    "published": published_bjt,
                }
            )
        print(json.dumps(stories, indent=2, ensure_ascii=False))
    else:
        # Text format
        feed_title = feed.feed.get("title", "RSS Feed")
        print(f"\n{feed_title}")
        print("=" * len(feed_title))
        print()

        for i, entry in enumerate(entries, 1):
            published_bjt, _published_iso = extract_entry_bjt_fields(entry)
            print(f"{i}. {entry.get('title', '')}")
            if hasattr(entry, "description") and entry.description:
                desc = strip_html(entry.description)
                print(f"""Content:\n```\n{desc}\n```""")
            print(f"Link: {entry.get('link', '')}")
            if published_bjt:
                print(f"Date: {published_bjt}")
            print()
    return 0


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Fetch news items from any RSS feed",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://feeds.bbci.co.uk/news/rss.xml
  %(prog)s https://feeds.bbci.co.uk/news/rss.xml --limit 5
  %(prog)s https://feeds.bbci.co.uk/news/rss.xml --format json
        """,
    )
    parser.add_argument("url", help="RSS feed URL")
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=15,
        help="Number of items to fetch (default: 15)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args(argv)

    return fetch_rss(args.url, args.limit, args.format)


if __name__ == "__main__":
    sys.exit(main())
