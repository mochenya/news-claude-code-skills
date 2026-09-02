from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from db import SQLiteStorage
from factions import FactionConfig
from models import normalize_username
from output import SH_TZ, print_faction_sync_results, print_json, print_query_results, print_sync_result
from rss_client import DEFAULT_BASE_URL, RSSClient
from service import SyncService

DEFAULT_FACTION_REQUEST_DELAY_MIN_SECONDS = 1.2
DEFAULT_FACTION_REQUEST_DELAY_MAX_SECONDS = 1.5


def _find_skill_dir() -> Path:
    if value := os.environ.get("SKILL_DIR"):
        return Path(value).expanduser().resolve()
    cwd = Path.cwd().resolve()
    if (cwd / "SKILL.md").exists() and (cwd / "pyproject.toml").exists():
        return cwd
    source_root = Path(__file__).resolve().parent.parent
    if (source_root / "SKILL.md").exists() and (source_root / "pyproject.toml").exists():
        return source_root
    return cwd


SKILL_DIR = _find_skill_dir()
DEFAULT_DB_PATH = SKILL_DIR / "data" / "data.db"
DEFAULT_FACTIONS_PATH = SKILL_DIR / "config" / "factions.json"


def parse_time_input(value: str) -> int:
    raw = value.strip()
    if not raw:
        raise ValueError("time value is empty")
    if raw.isdigit():
        return int(raw) // 1000 if len(raw) >= 13 else int(raw)

    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=SH_TZ)
        return int(dt.astimezone(timezone.utc).timestamp())
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=SH_TZ)
            return int(dt.astimezone(timezone.utc).timestamp())
        except ValueError:
            continue
    raise ValueError(
        f"Unsupported time format: {value!r}. Use unix ts, YYYY-MM-DD, local datetime, or ISO-8601."
    )


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("cannot be negative")
    return parsed


def _add_db_path(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="SQLite database path")


def _add_query_window(parser: argparse.ArgumentParser, *, default_limit: int) -> None:
    parser.add_argument("--start", required=True, help="Start time (unix ts / local datetime / ISO-8601)")
    parser.add_argument("--end", help="Exclusive end time; defaults to now")
    parser.add_argument("--limit", type=_positive_int, default=default_limit, help="Maximum posts to return")
    parser.add_argument("--json", action="store_true", help="Print one machine-readable JSON document")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect and query X posts from Nitter RSS with SQLite storage.")
    commands = parser.add_subparsers(dest="command", required=True)

    update = commands.add_parser("update", help="Incrementally update one account")
    _add_db_path(update)
    update.add_argument("username", help="X username, with or without @")
    update.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Nitter-compatible base URL")
    update.add_argument("--print-json", action="store_true", help="Print one JSON result including fetched posts")
    update.set_defaults(handler=run_update)

    query = commands.add_parser("query", help="Query one account by publication time")
    _add_db_path(query)
    query.add_argument("username", help="X username, with or without @")
    _add_query_window(query, default_limit=200)
    query.set_defaults(handler=run_query)

    update_faction = commands.add_parser("update-faction", help="Incrementally update one configured faction")
    _add_db_path(update_faction)
    update_faction.add_argument("faction", help="Faction name from factions.json")
    update_faction.add_argument("--factions-path", default=str(DEFAULT_FACTIONS_PATH), help="Faction config path")
    update_faction.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Nitter-compatible base URL")
    update_faction.add_argument("--concurrency", type=_positive_int, default=1, help="Concurrent fetch workers")
    update_faction.add_argument(
        "--request-delay-min",
        type=_non_negative_float,
        default=DEFAULT_FACTION_REQUEST_DELAY_MIN_SECONDS,
        help="Minimum delay between request starts",
    )
    update_faction.add_argument(
        "--request-delay-max",
        type=_non_negative_float,
        default=DEFAULT_FACTION_REQUEST_DELAY_MAX_SECONDS,
        help="Maximum delay between request starts",
    )
    update_faction.add_argument("--print-json", action="store_true", help="Print one JSON result including posts")
    update_faction.set_defaults(handler=run_update_faction)

    query_faction = commands.add_parser("query-faction", help="Query all accounts in one faction")
    _add_db_path(query_faction)
    query_faction.add_argument("faction", help="Faction name from factions.json")
    query_faction.add_argument("--factions-path", default=str(DEFAULT_FACTIONS_PATH), help="Faction config path")
    _add_query_window(query_faction, default_limit=500)
    query_faction.set_defaults(handler=run_query_faction)
    return parser


def _parse_window(start: str, end: str | None) -> tuple[int, int]:
    start_ts = parse_time_input(start)
    end_ts = parse_time_input(end) if end else int(datetime.now(timezone.utc).timestamp())
    if end_ts <= start_ts:
        raise ValueError("end must be greater than start")
    return start_ts, end_ts


def run_update(args: argparse.Namespace) -> int:
    username = normalize_username(args.username)
    with SQLiteStorage(args.db_path) as storage:
        result = SyncService(storage, RSSClient(base_url=args.base_url)).sync_account(username)

    if args.print_json:
        print_json(
            {
                "mode": "update",
                "database": str(Path(args.db_path).resolve()),
                "result": result.summary_dict(include_posts=True),
            }
        )
    else:
        print_sync_result(result, db_path=args.db_path)
    return 0 if result.status == "success" else 1


def run_query(args: argparse.Namespace) -> int:
    username = normalize_username(args.username)
    start_ts, end_ts = _parse_window(args.start, args.end)
    with SQLiteStorage(args.db_path) as storage:
        posts = storage.query_posts(username, start_ts=start_ts, end_ts=end_ts, limit=args.limit)

    if args.json:
        print_json(
            {
                "mode": "query",
                "query": {"username": username, "start_ts": start_ts, "end_ts": end_ts, "limit": args.limit},
                "count": len(posts),
                "posts": [post.to_dict() for post in posts],
            }
        )
    else:
        print_query_results(
            posts,
            title=f"查询用户: @{username}",
            start_ts=start_ts,
            end_ts=end_ts,
        )
    return 0


def run_update_faction(args: argparse.Namespace) -> int:
    faction = FactionConfig.load(args.factions_path).get(args.faction)
    if not faction.accounts:
        raise ValueError(f"Faction '{faction.name}' has no configured accounts")

    with SQLiteStorage(args.db_path) as storage:
        service = SyncService(storage, RSSClient(base_url=args.base_url))
        results = asyncio.run(
            service.sync_accounts(
                faction.accounts,
                concurrency=args.concurrency,
                request_delay_min=args.request_delay_min,
                request_delay_max=args.request_delay_max,
            )
        )

    failed_count = sum(result.status == "failed" for result in results)
    if args.print_json:
        print_json(
            {
                "mode": "update-faction",
                "faction": faction.name,
                "database": str(Path(args.db_path).resolve()),
                "account_count": len(faction.accounts),
                "success_count": len(results) - failed_count,
                "failed_count": failed_count,
                "results": [result.summary_dict(include_posts=True) for result in results],
            }
        )
    else:
        print_faction_sync_results(faction.name, results, db_path=args.db_path)
    return 1 if failed_count else 0


def run_query_faction(args: argparse.Namespace) -> int:
    faction = FactionConfig.load(args.factions_path).get(args.faction)
    if not faction.accounts:
        raise ValueError(f"Faction '{faction.name}' has no configured accounts")
    start_ts, end_ts = _parse_window(args.start, args.end)
    with SQLiteStorage(args.db_path) as storage:
        posts = storage.query_posts_for_accounts(
            faction.accounts,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=args.limit,
        )

    if args.json:
        print_json(
            {
                "mode": "query-faction",
                "query": {
                    "faction": faction.name,
                    "groups": faction.groups,
                    "accounts": faction.accounts,
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "limit": args.limit,
                },
                "count": len(posts),
                "posts": [post.to_dict() for post in posts],
            }
        )
    else:
        print_query_results(
            posts,
            title=f"查询阵营: {faction.name}",
            start_ts=start_ts,
            end_ts=end_ts,
            groups=faction.groups,
        )
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        code = args.handler(args)
    except (OSError, ValueError, RuntimeError) as exc:
        machine_output = bool(getattr(args, "json", False) or getattr(args, "print_json", False))
        if machine_output:
            print_json({"mode": args.command, "status": "failed", "error": str(exc)})
        else:
            print(f"错误: {exc}", file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
