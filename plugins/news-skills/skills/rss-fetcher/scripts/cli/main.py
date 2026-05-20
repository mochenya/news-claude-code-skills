from __future__ import annotations

import argparse
import sys
from typing import Callable

from . import news_fetch, news_query, news_sync, rss_fetch

CommandHandler = Callable[..., int]

COMMANDS: dict[str, tuple[str, CommandHandler, str]] = {
    "rss": ("Fetch a direct RSS URL", rss_fetch.main, "news rss"),
    "fetch": ("Fetch enabled sources by category", news_fetch.main, "news fetch"),
    "sync": ("Sync category feeds into SQLite", news_sync.main, "news sync"),
    "query": ("Query stored news from SQLite", news_query.main, "news query"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="news",
        description="RSS policy and AI news toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Commands:\n"
            "  rss    Fetch a direct RSS URL\n"
            "  fetch  Fetch enabled sources by category\n"
            "  sync   Sync category feeds into SQLite\n"
            "  query  Query stored news from SQLite\n\n"
            "Examples:\n"
            "  news fetch ai --limit 5\n"
            "  news sync middle-east\n"
            "  news query middle-east --since 24h\n"
            "  news rss https://feeds.bbci.co.uk/news/rss.xml --limit 5"
        ),
    )
    parser.add_argument("command", nargs="?", help="Subcommand to run")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the subcommand")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    command = COMMANDS.get(args.command)
    if command is None:
        parser.error(f"unknown command: {args.command}")

    command_argv = args.args
    if command_argv[:1] == ["--"]:
        command_argv = command_argv[1:]

    _, handler, prog = command
    return handler(command_argv, prog=prog)


if __name__ == "__main__":
    sys.exit(main())
