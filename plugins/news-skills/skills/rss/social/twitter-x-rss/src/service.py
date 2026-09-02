from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

import httpx

from db import SQLiteStorage
from models import ParsedFeed, SyncResult, normalize_username, utc_now_ts
from parser import parse_rss
from rss_client import RSSClient, RSSResponse


@dataclass(frozen=True, slots=True)
class _FetchAttempt:
    username: str
    requested_url: str
    started_ts: int
    finished_ts: int
    response: RSSResponse | None = None
    feed: ParsedFeed | None = None
    error: str | None = None
    http_status: int | None = None


class SyncService:
    def __init__(self, storage: SQLiteStorage, client: RSSClient):
        self.storage = storage
        self.client = client

    def sync_account(self, username: str) -> SyncResult:
        results = asyncio.run(
            self.sync_accounts(
                [username],
                concurrency=1,
                request_delay_min=0,
                request_delay_max=0,
            )
        )
        return results[0]

    async def sync_accounts(
        self,
        accounts: list[str],
        *,
        concurrency: int,
        request_delay_min: float,
        request_delay_max: float,
    ) -> list[SyncResult]:
        normalized_accounts: list[str] = []
        for account in accounts:
            username = normalize_username(account)
            if username and username not in normalized_accounts:
                normalized_accounts.append(username)
        if not normalized_accounts:
            return []
        if request_delay_min < 0 or request_delay_max < 0:
            raise ValueError("request delays cannot be negative")
        if request_delay_min > request_delay_max:
            raise ValueError("request_delay_min cannot be greater than request_delay_max")

        semaphore = asyncio.Semaphore(max(1, concurrency))
        request_lock = asyncio.Lock()
        next_request_at = 0.0

        async def wait_for_request_slot() -> None:
            nonlocal next_request_at
            if request_delay_max == 0:
                return
            async with request_lock:
                loop = asyncio.get_running_loop()
                now = loop.time()
                if now < next_request_at:
                    await asyncio.sleep(next_request_at - now)
                    now = loop.time()
                next_request_at = now + random.uniform(request_delay_min, request_delay_max)

        async def fetch(username: str, async_client: httpx.AsyncClient) -> _FetchAttempt:
            requested_url = self.client.build_rss_url(username)
            async with semaphore:
                await wait_for_request_slot()
                started_ts = utc_now_ts()
                response = None
                try:
                    response = await self.client.fetch_user_rss_async(username, client=async_client)
                    feed = parse_rss(response.xml_text, username=username, rss_url=response.rss_url)
                    return _FetchAttempt(
                        username=username,
                        requested_url=requested_url,
                        started_ts=started_ts,
                        finished_ts=utc_now_ts(),
                        response=response,
                        feed=feed,
                        http_status=response.status_code,
                    )
                except Exception as exc:
                    status = None
                    if isinstance(exc, httpx.HTTPStatusError):
                        status = exc.response.status_code
                    return _FetchAttempt(
                        username=username,
                        requested_url=requested_url,
                        started_ts=started_ts,
                        finished_ts=utc_now_ts(),
                        response=response,
                        error=f"{type(exc).__name__}: {exc}",
                        http_status=status or (response.status_code if response else None),
                    )

        async with self.client.create_async_client() as async_client:
            attempts = await asyncio.gather(*(fetch(username, async_client) for username in normalized_accounts))
        return [self._persist_attempt(attempt) for attempt in attempts]

    def _persist_attempt(self, attempt: _FetchAttempt) -> SyncResult:
        response = attempt.response
        feed = attempt.feed
        if attempt.error or response is None or feed is None:
            error = attempt.error or "fetch returned no response"
            self.storage.record_fetch_failure(
                attempt.username,
                requested_url=attempt.requested_url,
                final_url=response.final_url if response else None,
                started_ts=attempt.started_ts,
                finished_ts=attempt.finished_ts,
                error_message=error,
                http_status=attempt.http_status,
            )
            return SyncResult(
                username=attempt.username,
                status="failed",
                requested_url=attempt.requested_url,
                final_url=response.final_url if response else None,
                http_status=attempt.http_status,
                started_ts=attempt.started_ts,
                finished_ts=attempt.finished_ts,
                error=error,
            )

        try:
            stats = self.storage.save_feed(
                feed,
                requested_url=attempt.requested_url,
                final_url=response.final_url,
                started_ts=attempt.started_ts,
                finished_ts=attempt.finished_ts,
                http_status=response.status_code,
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            failed_ts = utc_now_ts()
            self.storage.record_fetch_failure(
                attempt.username,
                requested_url=attempt.requested_url,
                final_url=response.final_url,
                started_ts=attempt.started_ts,
                finished_ts=failed_ts,
                error_message=error,
                http_status=response.status_code,
            )
            return SyncResult(
                username=attempt.username,
                status="failed",
                requested_url=attempt.requested_url,
                final_url=response.final_url,
                http_status=response.status_code,
                started_ts=attempt.started_ts,
                finished_ts=failed_ts,
                source_item_count=feed.source_item_count,
                parsed_post_count=len(feed.posts),
                failed_item_count=feed.failed_item_count,
                error=error,
            )

        return SyncResult(
            username=attempt.username,
            status="success",
            requested_url=attempt.requested_url,
            final_url=response.final_url,
            http_status=response.status_code,
            started_ts=attempt.started_ts,
            finished_ts=attempt.finished_ts,
            source_item_count=feed.source_item_count,
            parsed_post_count=len(feed.posts),
            failed_item_count=feed.failed_item_count,
            stats=stats,
            posts=feed.posts,
        )
