from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from db import SQLiteStorage
from parser import parse_rss
from rss_client import RSSClient
from storage import JSONStorage

SH_TZ = ZoneInfo("Asia/Shanghai")


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
DEFAULT_DATA_DIR = SKILL_DIR / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "data.db"
DEFAULT_FACTIONS_PATH = SKILL_DIR / "config" / "factions.json"
DEFAULT_FACTION_REQUEST_DELAY_MIN_SECONDS = 1.2
DEFAULT_FACTION_REQUEST_DELAY_MAX_SECONDS = 1.5


def parse_time_input(value: str, *, default_tz: ZoneInfo = SH_TZ) -> int:
    raw = value.strip()
    if not raw:
        raise ValueError("time value is empty")

    # Unix timestamp in seconds / milliseconds
    if raw.isdigit():
        if len(raw) >= 13:
            return int(raw) // 1000
        return int(raw)

    # ISO 8601 with timezone or Z
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=default_tz)
        return int(dt.astimezone(timezone.utc).timestamp())
    except ValueError:
        pass

    # Common local datetime formats (interpreted as Asia/Shanghai)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=default_tz)
            return int(dt.astimezone(timezone.utc).timestamp())
        except ValueError:
            continue

    raise ValueError(
        f"Unsupported time format: {value!r}. Use unix ts, 'YYYY-MM-DD', 'YYYY-MM-DD HH:MM[:SS]' or ISO-8601."
    )


def format_ts_utc8(ts: int | None) -> str:
    if ts is None:
        return "-"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(SH_TZ)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC+8")


def _normalize_username(value: str) -> str:
    return value.strip().lstrip("@").lower()


def _normalize_accounts(accounts_raw: Any) -> list[str]:
    if not isinstance(accounts_raw, list):
        return []

    normalized_accounts: list[str] = []
    seen: set[str] = set()
    for account in accounts_raw:
        if not isinstance(account, str):
            continue
        user = _normalize_username(account)
        if not user or user in seen:
            continue
        seen.add(user)
        normalized_accounts.append(user)
    return normalized_accounts



def _load_factions(path: str) -> dict[str, dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise ValueError(f"Factions file not found: {p}")

    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Invalid factions JSON: root must be object")

    parsed: dict[str, dict[str, Any]] = {}
    for faction_name, value in raw.items():
        if isinstance(value, list):
            accounts = _normalize_accounts(value)
            groups = {"default": accounts}
            last_sync_ts = None
        elif isinstance(value, dict):
            last_sync_ts = value.get("last_sync_ts")
            groups_raw = value.get("groups")
            accounts_raw = value.get("accounts")

            if isinstance(groups_raw, dict):
                groups: dict[str, list[str]] = {}
                merged_accounts: list[str] = []
                seen: set[str] = set()
                for group_name, group_accounts_raw in groups_raw.items():
                    group_accounts = _normalize_accounts(group_accounts_raw)
                    groups[str(group_name)] = group_accounts
                    for account in group_accounts:
                        if account not in seen:
                            seen.add(account)
                            merged_accounts.append(account)
                accounts = merged_accounts
            else:
                accounts = _normalize_accounts(accounts_raw)
                groups = {"default": accounts}
        else:
            raise ValueError(f"Invalid faction entry for '{faction_name}'")

        if isinstance(last_sync_ts, str) and last_sync_ts.isdigit():
            last_sync_ts = int(last_sync_ts)
        elif not isinstance(last_sync_ts, int):
            last_sync_ts = None

        parsed[str(faction_name)] = {
            "accounts": accounts,
            "groups": groups,
            "last_sync_ts": last_sync_ts,
        }

    return parsed


def _save_factions(path: str, factions: dict[str, dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    serializable: dict[str, Any] = {}
    for faction_name, entry in factions.items():
        groups = entry.get("groups") or {"default": entry.get("accounts") or []}
        serializable[faction_name] = {
            "groups": groups,
            "last_sync_ts": entry.get("last_sync_ts"),
        }

    p.write_text(json.dumps(serializable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _get_faction(factions: dict[str, dict[str, Any]], faction_name: str) -> tuple[str, dict[str, Any]]:
    key = faction_name.strip()
    if key in factions:
        return key, factions[key]

    lowered = key.lower()
    for existing in factions:
        if existing.lower() == lowered:
            return existing, factions[existing]

    raise ValueError(f"Faction not found: {faction_name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect and query X posts from Nitter RSS with local SQLite storage.")

    subparsers = parser.add_subparsers(dest="command")

    update = subparsers.add_parser("update", help="Incrementally update posts for one username")
    update.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    update.add_argument("username", help="X username, e.g. elonmusk or @elonmusk")
    update.add_argument("--base-url", default="https://nitter.net", help="Nitter-compatible base URL")
    update.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Root directory for optional JSON archive")
    update.add_argument("--dump-feed", action="store_true", help="Save raw RSS XML into user folder for debugging")
    update.add_argument("--print-json", action="store_true", help="Print parsed posts JSON to stdout")
    update.add_argument(
        "--no-json-archive",
        action="store_true",
        help="Disable legacy JSON archive writes (SQLite will still be updated)",
    )

    query = subparsers.add_parser("query", help="Query local posts by username and time window")
    query.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    query.add_argument("username", help="X username, e.g. elonmusk or @elonmusk")
    query.add_argument("--start", required=True, help="Start time (unix ts / YYYY-MM-DD / datetime / ISO8601)")
    query.add_argument("--end", help="End time (exclusive). If omitted, defaults to now")
    query.add_argument("--limit", type=int, default=200, help="Max rows to print")
    query.add_argument("--json", action="store_true", help="Print query result as JSON")

    update_faction = subparsers.add_parser("update-faction", help="Incrementally update all accounts in a faction")
    update_faction.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    update_faction.add_argument("faction", help="Faction name defined in factions JSON, e.g. musk")
    update_faction.add_argument("--factions-path", default=str(DEFAULT_FACTIONS_PATH), help="Path to factions JSON")
    update_faction.add_argument("--base-url", default="https://nitter.net", help="Nitter-compatible base URL")
    update_faction.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Root directory for optional JSON archive")
    update_faction.add_argument("--dump-feed", action="store_true", help="Save raw RSS XML into user folder for debugging")
    update_faction.add_argument("--print-json", action="store_true", help="Print parsed posts JSON to stdout")
    update_faction.add_argument(
        "--no-json-archive",
        action="store_true",
        help="Disable legacy JSON archive writes (SQLite will still be updated)",
    )
    update_faction.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Concurrent fetch workers for faction update",
    )
    update_faction.add_argument(
        "--request-delay-min",
        type=float,
        default=DEFAULT_FACTION_REQUEST_DELAY_MIN_SECONDS,
        help="Minimum seconds to wait between faction RSS request starts",
    )
    update_faction.add_argument(
        "--request-delay-max",
        type=float,
        default=DEFAULT_FACTION_REQUEST_DELAY_MAX_SECONDS,
        help="Maximum seconds to wait between faction RSS request starts",
    )

    query_faction = subparsers.add_parser("query-faction", help="Query local posts for all accounts in a faction")
    query_faction.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    query_faction.add_argument("faction", help="Faction name defined in factions JSON, e.g. musk")
    query_faction.add_argument("--factions-path", default=str(DEFAULT_FACTIONS_PATH), help="Path to factions JSON")
    query_faction.add_argument("--start", required=True, help="Start time (unix ts / YYYY-MM-DD / datetime / ISO8601)")
    query_faction.add_argument("--end", help="End time (exclusive). If omitted, defaults to now")
    query_faction.add_argument("--limit", type=int, default=500, help="Max rows to print")
    query_faction.add_argument("--json", action="store_true", help="Print query result as JSON")

    return parser


def _update_one_account(
    *,
    username: str,
    base_url: str,
    data_dir: str,
    db: SQLiteStorage,
    dump_feed: bool,
    no_json_archive: bool,
) -> dict[str, Any]:
    username = _normalize_username(username)
    client = RSSClient(base_url=base_url)
    storage = JSONStorage(root=data_dir)

    rss_url = client.build_rss_url(username)
    run_id = db.start_fetch_run(username, rss_url)

    try:
        response = client.fetch_user_rss(username)
        parsed = parse_rss(response.xml_text, username=username, rss_url=response.rss_url)

        if dump_feed and not no_json_archive:
            user_dir = storage.user_dir(username)
            (user_dir / "latest.xml").write_text(response.xml_text, encoding="utf-8")

        sqlite_result = db.upsert_posts(
            username,
            display_name=parsed.display_name,
            source="nitter-rss",
            source_url=parsed.source_url,
            rss_url=response.final_url,
            posts=parsed.posts,
        )

        json_result = None
        if not no_json_archive:
            storage.update_user_meta_fields(
                username,
                source="nitter-rss",
                source_url=parsed.source_url,
                rss_url=response.final_url,
                display_name=parsed.display_name,
            )
            json_result = storage.upsert_posts(username, parsed.posts)

        db.finish_fetch_run(
            run_id,
            status="success",
            fetched_posts=len(parsed.posts),
            inserted_count=sqlite_result["inserted"],
            updated_count=sqlite_result["updated"],
        )

        result: dict[str, Any] = {
            "status": "success",
            "username": username,
            "display_name": parsed.display_name,
            "rss_url": response.final_url,
            "fetched_posts": len(parsed.posts),
            "sqlite": {
                "inserted": sqlite_result["inserted"],
                "updated": sqlite_result["updated"],
                "total_posts": sqlite_result["total_posts"],
                "last_post_id": sqlite_result["last_post_id"],
                "last_post_ts": sqlite_result["last_post_ts"],
                "last_post_utc8": format_ts_utc8(sqlite_result["last_post_ts"]),
            },
            "posts_json": [post.to_dict() for post in parsed.posts],
        }

        if json_result is not None:
            result["json_archive"] = {
                "enabled": True,
                "inserted": json_result["inserted"],
                "updated": json_result["updated"],
                "touched_dates": json_result["touched_dates"],
            }
        else:
            result["json_archive"] = {"enabled": False}

        return result

    except Exception as exc:
        db.finish_fetch_run(run_id, status="failed", error_message=str(exc))
        return {
            "status": "failed",
            "username": username,
            "error": str(exc),
        }


def _persist_fetched_account(
    *,
    username: str,
    response: Any,
    parsed: Any,
    data_dir: str,
    db: SQLiteStorage,
    dump_feed: bool,
    no_json_archive: bool,
) -> dict[str, Any]:
    storage = JSONStorage(root=data_dir)
    run_id = db.start_fetch_run(username, response.rss_url)

    try:
        if dump_feed and not no_json_archive:
            user_dir = storage.user_dir(username)
            (user_dir / "latest.xml").write_text(response.xml_text, encoding="utf-8")

        sqlite_result = db.upsert_posts(
            username,
            display_name=parsed.display_name,
            source="nitter-rss",
            source_url=parsed.source_url,
            rss_url=response.final_url,
            posts=parsed.posts,
        )

        json_result = None
        if not no_json_archive:
            storage.update_user_meta_fields(
                username,
                source="nitter-rss",
                source_url=parsed.source_url,
                rss_url=response.final_url,
                display_name=parsed.display_name,
            )
            json_result = storage.upsert_posts(username, parsed.posts)

        db.finish_fetch_run(
            run_id,
            status="success",
            fetched_posts=len(parsed.posts),
            inserted_count=sqlite_result["inserted"],
            updated_count=sqlite_result["updated"],
        )

        result: dict[str, Any] = {
            "status": "success",
            "username": username,
            "display_name": parsed.display_name,
            "rss_url": response.final_url,
            "fetched_posts": len(parsed.posts),
            "sqlite": {
                "inserted": sqlite_result["inserted"],
                "updated": sqlite_result["updated"],
                "total_posts": sqlite_result["total_posts"],
                "last_post_id": sqlite_result["last_post_id"],
                "last_post_ts": sqlite_result["last_post_ts"],
                "last_post_utc8": format_ts_utc8(sqlite_result["last_post_ts"]),
            },
            "posts_json": [post.to_dict() for post in parsed.posts],
        }

        if json_result is not None:
            result["json_archive"] = {
                "enabled": True,
                "inserted": json_result["inserted"],
                "updated": json_result["updated"],
                "touched_dates": json_result["touched_dates"],
            }
        else:
            result["json_archive"] = {"enabled": False}

        return result

    except Exception as exc:
        db.finish_fetch_run(run_id, status="failed", error_message=str(exc))
        return {
            "status": "failed",
            "username": username,
            "error": str(exc),
        }


async def _fetch_and_parse_accounts(
    *,
    accounts: list[str],
    base_url: str,
    concurrency: int,
    request_delay_min: float,
    request_delay_max: float,
) -> dict[str, dict[str, Any]]:
    client = RSSClient(base_url=base_url)
    sem = asyncio.Semaphore(max(1, concurrency))
    request_lock = asyncio.Lock()
    next_request_at = 0.0

    async def wait_for_request_slot() -> None:
        nonlocal next_request_at
        if request_delay_max <= 0:
            return

        async with request_lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            if now < next_request_at:
                await asyncio.sleep(next_request_at - now)
                now = loop.time()
            next_request_at = now + random.uniform(request_delay_min, request_delay_max)

    async def worker(username: str, shared_client: Any) -> tuple[str, dict[str, Any]]:
        normalized_username = _normalize_username(username)
        async with sem:
            try:
                await wait_for_request_slot()
                response = await client.fetch_user_rss_async(normalized_username, client=shared_client)
                parsed = parse_rss(response.xml_text, username=normalized_username, rss_url=response.rss_url)
                return normalized_username, {
                    "status": "success",
                    "response": response,
                    "parsed": parsed,
                }
            except Exception as exc:
                return normalized_username, {
                    "status": "failed",
                    "error": str(exc),
                    "rss_url": client.build_rss_url(normalized_username),
                }

    async with client.create_async_client() as shared_client:
        pairs = await asyncio.gather(*(worker(username, shared_client) for username in accounts))

    return {username: result for username, result in pairs}


def run_update(
    *,
    username: str,
    base_url: str,
    data_dir: str,
    db_path: str,
    dump_feed: bool,
    print_json: bool,
    no_json_archive: bool,
) -> int:
    with SQLiteStorage(db_path=db_path) as db:
        result = _update_one_account(
            username=username,
            base_url=base_url,
            data_dir=data_dir,
            db=db,
            dump_feed=dump_feed,
            no_json_archive=no_json_archive,
        )

    if result["status"] != "success":
        print(
            json.dumps(
                {
                    "mode": "update",
                    "username": _normalize_username(username),
                    "error": result.get("error") or "unknown error",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    summary = {
        "mode": "update",
        "username": result["username"],
        "display_name": result.get("display_name"),
        "rss_url": result.get("rss_url"),
        "fetched_posts": result.get("fetched_posts"),
        "sqlite": {
            "db_path": str(Path(db_path).resolve()),
            **(result.get("sqlite") or {}),
        },
        "json_archive": {
            **(result.get("json_archive") or {}),
            "data_dir": str(Path(data_dir).resolve()),
        },
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if print_json:
        print(json.dumps(result.get("posts_json") or [], ensure_ascii=False, indent=2))
    return 0


def _pretty_type(post_type: str) -> str:
    mapping = {
        "tweet": "普通贴文",
        "reply": "回复",
        "retweet": "转帖",
        "quote": "引用",
        "unknown": "未知",
    }
    return mapping.get(post_type, post_type)


def _render_original_post(item: dict) -> list[str]:
    original = item.get("original_post") or None
    if not isinstance(original, dict):
        return []

    lines: list[str] = []
    author = (original.get("author") or "").strip()
    content = (original.get("content") or "").strip()
    url = (original.get("url") or "").strip()
    post_id = (original.get("post_id") or "").strip()

    if author:
        lines.append(f"原贴作者: @{author}")
    if content:
        lines.append(f"原贴内容: {content}")
    if url:
        lines.append(f"原贴链接: {url}")
    elif post_id and author:
        lines.append(f"原贴链接: https://x.com/{author}/status/{post_id}")
    elif post_id:
        lines.append(f"原贴ID: {post_id}")

    return lines


def _print_one_item(item: dict, idx: int) -> None:
    print("\n" + "-" * 72)
    print(f"[{idx}] {_pretty_type(item['type'])} | {format_ts_utc8(item['created_ts'])}")
    account_user = (item.get("account_username") or "-").strip()
    author_user = (item.get("author_username") or "").strip()
    print(f"查询账号: @{account_user}")
    if author_user and author_user != account_user:
        print(f"内容作者: @{author_user}")
    print(f"推文链接: {item.get('url') or '-'}")

    text = (item.get("content_text") or "").strip()
    if text:
        print(f"发帖内容: {text}")
    else:
        title_text = (item.get("title") or "").strip()
        print(f"发帖内容: {title_text or '-'}")

    original_lines = _render_original_post(item)
    if original_lines:
        print("--- 原贴信息 ---")
        for line in original_lines:
            print(line)



def _print_query_human(
    rows: list[dict],
    *,
    title: str,
    start_ts: int,
    end_ts: int,
    last_sync_ts: int | None = None,
) -> None:
    print(title)
    print(f"时间区间: [{format_ts_utc8(start_ts)} , {format_ts_utc8(end_ts)})")
    if last_sync_ts is not None:
        print(f"上次同步: {format_ts_utc8(last_sync_ts)}")
    print(f"结果数量: {len(rows)}")

    if not rows:
        return

    for idx, item in enumerate(rows, start=1):
        _print_one_item(item, idx)



def _print_query_faction_grouped(
    rows: list[dict],
    *,
    faction_key: str,
    groups: dict[str, list[str]],
    start_ts: int,
    end_ts: int,
    last_sync_ts: int | None,
) -> None:
    print(f"查询大类: {faction_key}")
    print(f"时间区间: [{format_ts_utc8(start_ts)} , {format_ts_utc8(end_ts)})")
    if last_sync_ts is not None:
        print(f"上次同步: {format_ts_utc8(last_sync_ts)}")
    print(f"结果数量: {len(rows)}")

    if not rows:
        return

    account_to_group: dict[str, str] = {}
    for group_name, accounts in groups.items():
        for account in accounts:
            account_to_group[account] = group_name

    grouped: dict[str, dict[str, list[dict]]] = {}
    for item in rows:
        account = (item.get("account_username") or "").strip().lower()
        group_name = account_to_group.get(account, "ungrouped")
        grouped.setdefault(group_name, {}).setdefault(account, []).append(item)

    global_idx = 1
    for group_name, accounts in grouped.items():
        print(f"\n{'=' * 72}")
        print(f"小类: {group_name}")
        for account, account_rows in accounts.items():
            print(f"\n{'~' * 72}")
            print(f"账号: @{account} | {len(account_rows)} 条")
            for item in account_rows:
                _print_one_item(item, global_idx)
                global_idx += 1


def run_query(*, username: str, db_path: str, start: str, end: str | None, limit: int, as_json: bool) -> int:
    username = _normalize_username(username)

    try:
        start_ts = parse_time_input(start)
        end_ts = parse_time_input(end) if end else int(datetime.now(timezone.utc).timestamp())
    except ValueError as exc:
        print(json.dumps({"mode": "query", "username": username, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    if end_ts <= start_ts:
        print(
            json.dumps(
                {
                    "mode": "query",
                    "username": username,
                    "error": "Invalid window: end must be greater than start",
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    with SQLiteStorage(db_path=db_path) as db:
        rows = db.query_posts(username, start_ts=start_ts, end_ts=end_ts, limit=limit)

    if as_json:
        print(
            json.dumps(
                {
                    "mode": "query",
                    "username": username,
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "count": len(rows),
                    "rows": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_query_human(rows, title=f"查询用户: @{username}", start_ts=start_ts, end_ts=end_ts)

    return 0


def run_update_faction(
    *,
    faction: str,
    factions_path: str,
    base_url: str,
    data_dir: str,
    db_path: str,
    dump_feed: bool,
    print_json: bool,
    no_json_archive: bool,
    concurrency: int,
    request_delay_min: float,
    request_delay_max: float,
) -> int:
    request_delay_min = max(0.0, request_delay_min)
    request_delay_max = max(0.0, request_delay_max)
    if request_delay_min > request_delay_max:
        print(
            json.dumps(
                {
                    "mode": "update-faction",
                    "faction": faction,
                    "error": "--request-delay-min must be less than or equal to --request-delay-max",
                    "request_delay_min": request_delay_min,
                    "request_delay_max": request_delay_max,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    try:
        factions = _load_factions(factions_path)
        faction_key, faction_entry = _get_faction(factions, faction)
    except ValueError as exc:
        print(json.dumps({"mode": "update-faction", "faction": faction, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    accounts = faction_entry.get("accounts") or []
    if not accounts:
        print(
            json.dumps(
                {
                    "mode": "update-faction",
                    "faction": faction_key,
                    "error": "No accounts configured in faction",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    fetched = asyncio.run(
        _fetch_and_parse_accounts(
            accounts=accounts,
            base_url=base_url,
            concurrency=concurrency,
            request_delay_min=request_delay_min,
            request_delay_max=request_delay_max,
        )
    )

    results: list[dict[str, Any]] = []
    with SQLiteStorage(db_path=db_path) as db:
        for username in accounts:
            normalized_username = _normalize_username(username)
            item = fetched.get(normalized_username)

            if not item:
                rss_url = RSSClient(base_url=base_url).build_rss_url(normalized_username)
                run_id = db.start_fetch_run(normalized_username, rss_url)
                db.finish_fetch_run(run_id, status="failed", error_message="missing fetch result")
                results.append(
                    {
                        "status": "failed",
                        "username": normalized_username,
                        "error": "missing fetch result",
                    }
                )
                continue

            if item.get("status") != "success":
                rss_url = item.get("rss_url") or RSSClient(base_url=base_url).build_rss_url(normalized_username)
                run_id = db.start_fetch_run(normalized_username, rss_url)
                db.finish_fetch_run(run_id, status="failed", error_message=item.get("error") or "unknown error")
                results.append(
                    {
                        "status": "failed",
                        "username": normalized_username,
                        "error": item.get("error") or "unknown error",
                    }
                )
                continue

            r = _persist_fetched_account(
                username=normalized_username,
                response=item["response"],
                parsed=item["parsed"],
                data_dir=data_dir,
                db=db,
                dump_feed=dump_feed,
                no_json_archive=no_json_archive,
            )
            results.append(r)

    success_count = sum(1 for r in results if r.get("status") == "success")
    failed_count = len(results) - success_count

    now_ts = int(datetime.now(timezone.utc).timestamp())
    factions[faction_key]["last_sync_ts"] = now_ts
    _save_factions(factions_path, factions)

    summary: dict[str, Any] = {
        "mode": "update-faction",
        "faction": faction_key,
        "factions_path": str(Path(factions_path).resolve()),
        "db_path": str(Path(db_path).resolve()),
        "account_count": len(accounts),
        "request_delay_seconds": {
            "min": request_delay_min,
            "max": request_delay_max,
        },
        "success_count": success_count,
        "failed_count": failed_count,
        "last_sync_ts": now_ts,
        "last_sync_utc8": format_ts_utc8(now_ts),
        "results": [],
    }

    for r in results:
        if r.get("status") == "success":
            item: dict[str, Any] = {
                "status": "success",
                "username": r["username"],
                "fetched_posts": r.get("fetched_posts"),
                "sqlite": r.get("sqlite") or {},
            }
            if print_json:
                item["posts_json"] = r.get("posts_json") or []
            summary["results"].append(item)
        else:
            summary["results"].append(
                {
                    "status": "failed",
                    "username": r.get("username"),
                    "error": r.get("error") or "unknown error",
                }
            )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if failed_count == 0 else 1


def run_query_faction(
    *,
    faction: str,
    factions_path: str,
    db_path: str,
    start: str,
    end: str | None,
    limit: int,
    as_json: bool,
) -> int:
    try:
        factions = _load_factions(factions_path)
        faction_key, faction_entry = _get_faction(factions, faction)
    except ValueError as exc:
        print(json.dumps({"mode": "query-faction", "faction": faction, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    accounts = faction_entry.get("accounts") or []
    groups = faction_entry.get("groups") or {"default": accounts}
    last_sync_ts = faction_entry.get("last_sync_ts")
    if not accounts:
        print(
            json.dumps(
                {
                    "mode": "query-faction",
                    "faction": faction_key,
                    "error": "No accounts configured in faction",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    try:
        start_ts = parse_time_input(start)
        end_ts = parse_time_input(end) if end else int(datetime.now(timezone.utc).timestamp())
    except ValueError as exc:
        print(json.dumps({"mode": "query-faction", "faction": faction_key, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    if end_ts <= start_ts:
        print(
            json.dumps(
                {
                    "mode": "query-faction",
                    "faction": faction_key,
                    "error": "Invalid window: end must be greater than start",
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    with SQLiteStorage(db_path=db_path) as db:
        rows = db.query_posts_for_accounts(accounts, start_ts=start_ts, end_ts=end_ts, limit=limit)

    if as_json:
        print(
            json.dumps(
                {
                    "mode": "query-faction",
                    "faction": faction_key,
                    "groups": groups,
                    "accounts": accounts,
                    "last_sync_ts": last_sync_ts,
                    "last_sync_utc8": format_ts_utc8(last_sync_ts),
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "count": len(rows),
                    "rows": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_query_faction_grouped(
            rows,
            faction_key=faction_key,
            groups=groups,
            start_ts=start_ts,
            end_ts=end_ts,
            last_sync_ts=last_sync_ts,
        )

    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "update":
        code = run_update(
            username=args.username,
            base_url=args.base_url,
            data_dir=args.data_dir,
            db_path=args.db_path,
            dump_feed=args.dump_feed,
            print_json=args.print_json,
            no_json_archive=args.no_json_archive,
        )
        raise SystemExit(code)

    if args.command == "query":
        code = run_query(
            username=args.username,
            db_path=args.db_path,
            start=args.start,
            end=args.end,
            limit=args.limit,
            as_json=args.json,
        )
        raise SystemExit(code)

    if args.command == "update-faction":
        code = run_update_faction(
            faction=args.faction,
            factions_path=args.factions_path,
            base_url=args.base_url,
            data_dir=args.data_dir,
            db_path=args.db_path,
            dump_feed=args.dump_feed,
            print_json=args.print_json,
            no_json_archive=args.no_json_archive,
            concurrency=args.concurrency,
            request_delay_min=args.request_delay_min,
            request_delay_max=args.request_delay_max,
        )
        raise SystemExit(code)

    if args.command == "query-faction":
        code = run_query_faction(
            faction=args.faction,
            factions_path=args.factions_path,
            db_path=args.db_path,
            start=args.start,
            end=args.end,
            limit=args.limit,
            as_json=args.json,
        )
        raise SystemExit(code)

    parser.print_help()
    raise SystemExit(1)


if __name__ == "__main__":
    main()
