from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from models import PostRecord


def iso_to_ts(value: str | None) -> int | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def stable_payload_json(payload: dict) -> str:
    normalized = dict(payload)
    # fetched_at is volatile for each run and should not count as content change
    normalized.pop("fetched_at", None)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class SQLiteStorage:
    def __init__(self, db_path: str | Path = "data/data.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SQLiteStorage":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                username TEXT PRIMARY KEY,
                display_name TEXT,
                source TEXT,
                source_url TEXT,
                rss_url TEXT,
                last_checked_ts INTEGER,
                last_post_ts INTEGER,
                last_post_id TEXT,
                total_posts INTEGER DEFAULT 0,
                created_at_ts INTEGER NOT NULL,
                updated_at_ts INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tweets (
                post_id TEXT PRIMARY KEY,
                account_username TEXT NOT NULL,
                author_username TEXT,
                display_name TEXT,
                type TEXT NOT NULL,
                title TEXT,
                content_text TEXT,
                content_html TEXT,
                url TEXT,
                source_url TEXT,
                published_at TEXT NOT NULL,
                created_ts INTEGER NOT NULL,
                fetched_at TEXT,
                fetched_ts INTEGER,
                guid TEXT,
                original_post_json TEXT,
                tags_json TEXT,
                raw_json TEXT,
                first_seen_ts INTEGER NOT NULL,
                last_seen_ts INTEGER NOT NULL,
                FOREIGN KEY(account_username) REFERENCES accounts(username)
            );

            CREATE TABLE IF NOT EXISTS fetch_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_username TEXT NOT NULL,
                rss_url TEXT,
                started_ts INTEGER NOT NULL,
                finished_ts INTEGER,
                status TEXT NOT NULL,
                fetched_posts INTEGER,
                inserted_count INTEGER,
                updated_count INTEGER,
                error_message TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_tweets_account_created_ts
            ON tweets(account_username, created_ts DESC);

            CREATE INDEX IF NOT EXISTS idx_fetch_runs_account_started_ts
            ON fetch_runs(account_username, started_ts DESC);
            """
        )
        self.conn.commit()

    def start_fetch_run(self, username: str, rss_url: str) -> int:
        started_ts = int(time.time())
        cursor = self.conn.execute(
            """
            INSERT INTO fetch_runs(account_username, rss_url, started_ts, status)
            VALUES (?, ?, ?, 'running')
            """,
            (username, rss_url, started_ts),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def finish_fetch_run(
        self,
        run_id: int,
        *,
        status: str,
        fetched_posts: int | None = None,
        inserted_count: int | None = None,
        updated_count: int | None = None,
        error_message: str | None = None,
    ) -> None:
        finished_ts = int(time.time())
        self.conn.execute(
            """
            UPDATE fetch_runs
            SET finished_ts = ?, status = ?, fetched_posts = ?, inserted_count = ?, updated_count = ?, error_message = ?
            WHERE id = ?
            """,
            (finished_ts, status, fetched_posts, inserted_count, updated_count, error_message, run_id),
        )
        self.conn.commit()

    def _upsert_account(
        self,
        username: str,
        *,
        display_name: str | None,
        source: str,
        source_url: str,
        rss_url: str,
    ) -> None:
        now_ts = int(time.time())
        self.conn.execute(
            """
            INSERT INTO accounts(
                username, display_name, source, source_url, rss_url,
                last_checked_ts, created_at_ts, updated_at_ts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                display_name = excluded.display_name,
                source = excluded.source,
                source_url = excluded.source_url,
                rss_url = excluded.rss_url,
                last_checked_ts = excluded.last_checked_ts,
                updated_at_ts = excluded.updated_at_ts
            """,
            (username, display_name, source, source_url, rss_url, now_ts, now_ts, now_ts),
        )

    def upsert_posts(
        self,
        username: str,
        *,
        display_name: str | None,
        source: str,
        source_url: str,
        rss_url: str,
        posts: list[PostRecord],
    ) -> dict:
        inserted = 0
        updated = 0
        now_ts = int(time.time())

        self.conn.execute("BEGIN")
        try:
            self._upsert_account(
                username,
                display_name=display_name,
                source=source,
                source_url=source_url,
                rss_url=rss_url,
            )

            for post in posts:
                payload = post.to_dict()
                created_ts = iso_to_ts(post.published_at)
                fetched_ts = iso_to_ts(post.fetched_at)
                if created_ts is None:
                    continue

                original_post_json = None
                if payload.get("original_post") is not None:
                    original_post_json = json.dumps(payload["original_post"], ensure_ascii=False)
                tags_json = json.dumps(payload.get("tags", []), ensure_ascii=False)
                raw_json = json.dumps(payload, ensure_ascii=False)
                stable_json = stable_payload_json(payload)

                existing = self.conn.execute(
                    "SELECT raw_json, fetched_ts FROM tweets WHERE post_id = ?",
                    (post.post_id,),
                ).fetchone()

                if existing is None:
                    self.conn.execute(
                        """
                        INSERT INTO tweets(
                            post_id, account_username, author_username, display_name, type, title,
                            content_text, content_html, url, source_url, published_at, created_ts,
                            fetched_at, fetched_ts, guid, original_post_json, tags_json, raw_json,
                            first_seen_ts, last_seen_ts
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            post.post_id,
                            username,
                            post.author_username,
                            post.display_name,
                            post.type,
                            post.title,
                            post.content_text,
                            post.content_html,
                            post.url,
                            post.source_url,
                            post.published_at,
                            created_ts,
                            post.fetched_at,
                            fetched_ts,
                            post.guid,
                            original_post_json,
                            tags_json,
                            raw_json,
                            now_ts,
                            now_ts,
                        ),
                    )
                    inserted += 1
                else:
                    previous_raw_json = existing["raw_json"] or ""
                    try:
                        previous_payload = json.loads(previous_raw_json) if previous_raw_json else {}
                    except json.JSONDecodeError:
                        previous_payload = {}
                    previous_stable_json = stable_payload_json(previous_payload) if previous_payload else ""

                    changed = previous_stable_json != stable_json
                    prev_fetched_ts = existing["fetched_ts"]
                    if changed:
                        self.conn.execute(
                            """
                            UPDATE tweets
                            SET account_username = ?, author_username = ?, display_name = ?, type = ?, title = ?,
                                content_text = ?, content_html = ?, url = ?, source_url = ?,
                                published_at = ?, created_ts = ?, fetched_at = ?, fetched_ts = ?, guid = ?,
                                original_post_json = ?, tags_json = ?, raw_json = ?, last_seen_ts = ?
                            WHERE post_id = ?
                            """,
                            (
                                username,
                                post.author_username,
                                post.display_name,
                                post.type,
                                post.title,
                                post.content_text,
                                post.content_html,
                                post.url,
                                post.source_url,
                                post.published_at,
                                created_ts,
                                post.fetched_at,
                                fetched_ts,
                                post.guid,
                                original_post_json,
                                tags_json,
                                raw_json,
                                now_ts,
                                post.post_id,
                            ),
                        )
                        updated += 1
                    else:
                        self.conn.execute(
                            """
                            UPDATE tweets
                            SET last_seen_ts = ?,
                                fetched_ts = COALESCE(fetched_ts, ?),
                                fetched_at = COALESCE(fetched_at, ?)
                            WHERE post_id = ?
                            """,
                            (
                                now_ts,
                                fetched_ts if fetched_ts is not None else prev_fetched_ts,
                                post.fetched_at,
                                post.post_id,
                            ),
                        )

            stat = self.conn.execute(
                """
                SELECT COUNT(*) AS total_posts, MAX(created_ts) AS last_post_ts
                FROM tweets
                WHERE account_username = ?
                """,
                (username,),
            ).fetchone()
            total_posts = int(stat["total_posts"] or 0)
            last_post_ts = stat["last_post_ts"]

            last_post_row = self.conn.execute(
                """
                SELECT post_id FROM tweets
                WHERE account_username = ?
                ORDER BY created_ts DESC, post_id DESC
                LIMIT 1
                """,
                (username,),
            ).fetchone()
            last_post_id = last_post_row["post_id"] if last_post_row else None

            self.conn.execute(
                """
                UPDATE accounts
                SET total_posts = ?, last_post_ts = ?, last_post_id = ?,
                    last_checked_ts = ?, updated_at_ts = ?
                WHERE username = ?
                """,
                (total_posts, last_post_ts, last_post_id, now_ts, now_ts, username),
            )

            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return {
            "inserted": inserted,
            "updated": updated,
            "total_posts": total_posts,
            "last_post_ts": last_post_ts,
            "last_post_id": last_post_id,
        }

    def _decode_tweet_row(self, row: sqlite3.Row) -> dict:
        item = dict(row)
        if item.get("original_post_json"):
            item["original_post"] = json.loads(item["original_post_json"])
        else:
            item["original_post"] = None
        item.pop("original_post_json", None)

        if item.get("tags_json"):
            item["tags"] = json.loads(item["tags_json"])
        else:
            item["tags"] = []
        item.pop("tags_json", None)
        return item

    def query_posts(self, username: str, *, start_ts: int, end_ts: int, limit: int = 200) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT
                post_id,
                account_username,
                author_username,
                display_name,
                type,
                title,
                content_text,
                content_html,
                url,
                source_url,
                published_at,
                created_ts,
                fetched_at,
                fetched_ts,
                guid,
                original_post_json,
                tags_json,
                first_seen_ts,
                last_seen_ts
            FROM tweets
            WHERE account_username = ?
              AND created_ts >= ?
              AND created_ts < ?
            ORDER BY created_ts ASC, post_id ASC
            LIMIT ?
            """,
            (username, start_ts, end_ts, max(limit, 1)),
        ).fetchall()
        return [self._decode_tweet_row(row) for row in rows]

    def query_posts_for_accounts(self, accounts: list[str], *, start_ts: int, end_ts: int, limit: int = 500) -> list[dict]:
        normalized_accounts = [a.strip().lstrip("@").lower() for a in accounts if a and a.strip()]
        if not normalized_accounts:
            return []

        placeholders = ",".join(["?"] * len(normalized_accounts))
        sql = f"""
            SELECT
                post_id,
                account_username,
                author_username,
                display_name,
                type,
                title,
                content_text,
                content_html,
                url,
                source_url,
                published_at,
                created_ts,
                fetched_at,
                fetched_ts,
                guid,
                original_post_json,
                tags_json,
                first_seen_ts,
                last_seen_ts
            FROM tweets
            WHERE account_username IN ({placeholders})
              AND created_ts >= ?
              AND created_ts < ?
            ORDER BY created_ts ASC, post_id ASC
            LIMIT ?
        """
        params: list = [*normalized_accounts, start_ts, end_ts, max(limit, 1)]
        rows = self.conn.execute(sql, params).fetchall()
        return [self._decode_tweet_row(row) for row in rows]
