"""Batch RSS News Fetcher - Fetch news from multiple RSS sources organized by category."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

try:
    import feedparser
except ImportError:
    print(
        "Error: feedparser library not found. Install with: uv sync",
        file=sys.stderr,
    )
    sys.exit(1)

from lib.network import configure_network_timeout
from lib.source_registry import build_category_lookup, load_source_registry
from lib.text_utils import clean_html
from lib.time_utils import extract_entry_bjt_fields

configure_network_timeout()


def entry_to_story(entry: Any, source_name: str, category_key: str) -> dict[str, Any]:
    published_bjt, published_iso = extract_entry_bjt_fields(entry)
    description = clean_html(entry.get("description", "") or entry.get("summary", ""))
    return {
        "category": category_key,
        "source": source_name,
        "title": clean_html(entry.get("title", "")),
        "link": entry.get("link", ""),
        "description": description,
        "published": published_bjt,
        "published_iso": published_iso,
    }


def fetch_rss(url: str, source_name: str, category_key: str, limit: int = 15, output_format: str = "text"):
    feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        print(f"Error: Failed to parse feed from {source_name} ({url})", file=sys.stderr)
        if hasattr(feed, "bozo_exception"):
            print(f"  Reason: {feed.bozo_exception}", file=sys.stderr)
        return None

    entries = feed.entries[:limit]
    stories = [entry_to_story(entry, source_name, category_key) for entry in entries]

    if output_format == "json":
        return stories

    feed_title = feed.feed.get("title", source_name)
    result = [f"\n{feed_title}", "=" * len(feed_title), ""]
    for i, story in enumerate(stories, 1):
        result.append(f"{i}. {story['title']}")
        if story["description"]:
            desc = story["description"]
            if len(desc) > 200:
                desc = desc[:197] + "..."
            result.append(f"""content:\n```\n{desc}\n```""")
        result.append(f"Link: {story['link']}")
        if story["published"]:
            result.append(f"Date: {story['published']}")
        result.append("")
    return "\n".join(result)


def fetch_category(category_name: str, limit: int = 15, output_format: str = "text") -> int:
    categories = load_source_registry()
    category_lookup = build_category_lookup(categories)
    if category_name not in category_lookup:
        print(f"Error: Unknown category '{category_name}'", file=sys.stderr)
        print(f"Available categories: {', '.join(sorted(category_lookup.keys()))}", file=sys.stderr)
        return 1

    category = category_lookup[category_name]
    sources = [source for source in category.sources if source.enabled]
    failed = 0

    if output_format == "json":
        all_stories = []
        for source in sources:
            stories = fetch_rss(source.url, source.name, category.key, limit, output_format)
            if stories is None:
                failed += 1
            elif stories:
                all_stories.extend(stories)
        print(json.dumps(all_stories, indent=2, ensure_ascii=False))
    else:
        for source in sources:
            output = fetch_rss(source.url, source.name, category.key, limit, output_format)
            if output is None:
                failed += 1
            elif output:
                print(output)
    return 2 if failed else 0


def fetch_all_categories(limit: int = 15, output_format: str = "text") -> int:
    categories = [category for category in load_source_registry() if category.enabled]
    failed = 0
    if output_format == "json":
        all_stories = []
        for category in categories:
            for source in category.sources:
                if not source.enabled:
                    continue
                stories = fetch_rss(source.url, source.name, category.key, limit, output_format)
                if stories is None:
                    failed += 1
                elif stories:
                    all_stories.extend(stories)
        print(json.dumps(all_stories, indent=2, ensure_ascii=False))
    else:
        for category in categories:
            print(f"\n{'=' * 60}")
            print(f"Category: {category.key} - {category.name}")
            print(f"{'=' * 60}")
            for source in category.sources:
                if not source.enabled:
                    continue
                output = fetch_rss(source.url, source.name, category.key, limit, output_format)
                if output is None:
                    failed += 1
                elif output:
                    print(output)
    return 2 if failed else 0


def list_categories() -> None:
    categories = [category for category in load_source_registry() if category.enabled]
    print("\nAvailable Categories:")
    print("=" * 60)
    for category in categories:
        enabled_sources = [source for source in category.sources if source.enabled]
        print(f"\n{category.key:15} - {category.name}")
        print(f"{'':15}  Sources: {len(enabled_sources)}")
        for source in enabled_sources:
            print(f"{'':15}    • {source.name}")
    print()


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Fetch news from multiple RSS sources organized by category",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s top                        # Fetch top/headline news
  %(prog)s world --limit 5            # Fetch world news (5 items per source)
  %(prog)s middle-east --format json  # Middle East news in JSON format
  %(prog)s --list                     # List all categories and sources
  %(prog)s --all                      # Fetch from all categories
        """,
    )
    parser.add_argument("category", nargs="?", help="Category to fetch (use --list to see all categories)")
    parser.add_argument("-l", "--limit", type=int, default=15, help="Number of items to fetch per source (default: 15)")
    parser.add_argument("-f", "--format", choices=["text", "json"], default="text", help="Output format (default: text)")
    parser.add_argument("--list", action="store_true", help="List all available categories with their sources")
    parser.add_argument("--all", action="store_true", help="Fetch from all categories")
    args = parser.parse_args(argv)

    if args.list:
        list_categories()
        return 0
    if args.all:
        return fetch_all_categories(args.limit, args.format)
    if not args.category:
        parser.print_help(file=sys.stderr)
        print("\nError: Please specify a category or use --list to see available categories", file=sys.stderr)
        return 1
    return fetch_category(args.category, args.limit, args.format)


if __name__ == "__main__":
    sys.exit(main())
