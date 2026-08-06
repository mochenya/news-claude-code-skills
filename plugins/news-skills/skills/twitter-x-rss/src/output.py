from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from models import FeedPost, SyncResult

SH_TZ = ZoneInfo("Asia/Shanghai")


def format_ts(ts: int | None) -> str:
    if ts is None:
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(SH_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def sync_result_payload(result: SyncResult, *, include_posts: bool) -> dict:
    return result.summary_dict(include_posts=include_posts)


def print_sync_result(result: SyncResult, *, db_path: str) -> None:
    if result.status == "failed":
        print(f"@{result.username} 同步失败: {result.error or 'unknown error'}")
        return

    stats = result.stats
    assert stats is not None
    print(f"@{result.username} 同步完成")
    print(
        f"抓取 {result.source_item_count} 条，解析 {result.parsed_post_count} 条，"
        f"跳过 {result.failed_item_count} 条"
    )
    print(
        f"帖子新增 {stats.inserted_posts}、更新 {stats.updated_posts}；"
        f"账号关联新增 {stats.inserted_account_posts}、更新 {stats.updated_account_posts}"
    )
    print(f"账号库存 {stats.total_account_posts} 条，最新发布 {format_ts(stats.last_post_ts)}")
    print(f"数据库: {Path(db_path).resolve()}")


def print_faction_sync_results(faction: str, results: list[SyncResult], *, db_path: str) -> None:
    success_count = sum(result.status == "success" for result in results)
    print(f"阵营 {faction}: {success_count}/{len(results)} 个账号同步成功")
    for result in results:
        if result.status == "failed":
            print(f"- @{result.username}: 失败，{result.error or 'unknown error'}")
            continue
        stats = result.stats
        assert stats is not None
        print(
            f"- @{result.username}: 抓取 {result.source_item_count}，"
            f"新关联 {stats.inserted_account_posts}，更新 {stats.updated_account_posts}，"
            f"库存 {stats.total_account_posts}"
        )
    print(f"数据库: {Path(db_path).resolve()}")


def _pretty_type(post_type: str) -> str:
    return {
        "tweet": "普通贴文",
        "reply": "回复",
        "retweet": "转帖",
        "quote": "引用",
        "unknown": "未知",
    }.get(post_type, post_type)


def _print_post(post: FeedPost, index: int, *, show_account: bool) -> None:
    print("\n" + "-" * 72)
    print(f"[{index}] {_pretty_type(post.display_type)} | {format_ts(post.post.published_ts)}")
    if show_account:
        print(f"查询账号: @{post.account_username}")
    if post.post.author_username != post.account_username or post.relationship == "reposted":
        print(f"内容作者: @{post.post.author_username}")
    print(f"发帖内容: {post.post.content_text or post.feed_title or '-'}")
    print(f"推文链接: {post.post.url}")

    referenced = post.post.referenced_post
    if referenced:
        print("--- 关联原贴 ---")
        if referenced.author_username:
            print(f"作者: @{referenced.author_username}")
        if referenced.content_text:
            print(f"内容: {referenced.content_text}")
        if referenced.url:
            print(f"链接: {referenced.url}")
        elif referenced.post_id:
            print(f"帖子 ID: {referenced.post_id}")


def print_query_results(
    rows: list[FeedPost],
    *,
    title: str,
    start_ts: int,
    end_ts: int,
    groups: dict[str, list[str]] | None = None,
) -> None:
    print(title)
    print(f"时间区间: [{format_ts(start_ts)}, {format_ts(end_ts)})")
    print(f"结果数量: {len(rows)}")
    if not rows:
        return

    if groups is None:
        for index, row in enumerate(rows, start=1):
            _print_post(row, index, show_account=False)
        return

    rows_by_account: dict[str, list[FeedPost]] = {}
    for row in rows:
        rows_by_account.setdefault(row.account_username, []).append(row)

    index = 1
    for group_name, accounts in groups.items():
        visible_accounts = [account for account in accounts if account in rows_by_account]
        if not visible_accounts:
            continue
        print(f"\n{'=' * 72}\n小类: {group_name}")
        for account in visible_accounts:
            account_rows = rows_by_account.pop(account)
            print(f"\n{'~' * 72}\n账号: @{account} | {len(account_rows)} 条")
            for row in account_rows:
                _print_post(row, index, show_account=False)
                index += 1

    if rows_by_account:
        print(f"\n{'=' * 72}\n小类: ungrouped")
        for account, account_rows in rows_by_account.items():
            print(f"\n{'~' * 72}\n账号: @{account} | {len(account_rows)} 条")
            for row in account_rows:
                _print_post(row, index, show_account=False)
                index += 1
