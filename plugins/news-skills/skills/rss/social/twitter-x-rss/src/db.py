from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import cast

from models import (
    AccountPostRelationship,
    FeedPost,
    ParsedFeed,
    Post,
    PostKind,
    ReferencedPost,
    StorageStats,
    normalize_username,
)

SCHEMA_VERSION = 2
REQUIRED_TABLES = {
    "schema_version",
    "accounts",
    "posts",
    "account_posts",
    "source_items",
    "fetch_runs",
}

SCHEMA_SQL = """
CREATE TABLE schema_version (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    version INTEGER NOT NULL
);

INSERT INTO schema_version(singleton, version) VALUES (1, 2);

CREATE TABLE accounts (
    username TEXT PRIMARY KEY COLLATE NOCASE,
    display_name TEXT,
    source TEXT NOT NULL,
    profile_url TEXT,
    feed_url TEXT NOT NULL,
    last_checked_ts INTEGER,
    last_success_ts INTEGER,
    last_post_ts INTEGER,
    last_post_id TEXT,
    total_posts INTEGER NOT NULL DEFAULT 0 CHECK (total_posts >= 0),
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL
);

CREATE TABLE posts (
    post_id TEXT PRIMARY KEY,
    author_username TEXT NOT NULL COLLATE NOCASE,
    kind TEXT NOT NULL CHECK (kind IN ('tweet', 'reply', 'quote', 'unknown')),
    content_text TEXT NOT NULL DEFAULT '',
    content_html TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    published_ts INTEGER NOT NULL,
    referenced_post_id TEXT,
    referenced_author_username TEXT COLLATE NOCASE,
    referenced_content_text TEXT,
    referenced_url TEXT,
    first_seen_ts INTEGER NOT NULL,
    last_seen_ts INTEGER NOT NULL
);

CREATE TABLE account_posts (
    account_username TEXT NOT NULL COLLATE NOCASE,
    post_id TEXT NOT NULL,
    relationship TEXT NOT NULL CHECK (relationship IN ('authored', 'reposted')),
    feed_title TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    guid TEXT,
    first_seen_ts INTEGER NOT NULL,
    last_seen_ts INTEGER NOT NULL,
    PRIMARY KEY (account_username, post_id),
    FOREIGN KEY (account_username) REFERENCES accounts(username) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
);

CREATE TABLE source_items (
    account_username TEXT NOT NULL COLLATE NOCASE,
    post_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    raw_xml TEXT NOT NULL,
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL,
    PRIMARY KEY (account_username, post_id),
    FOREIGN KEY (account_username, post_id)
        REFERENCES account_posts(account_username, post_id) ON DELETE CASCADE
);

CREATE TABLE fetch_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_username TEXT NOT NULL COLLATE NOCASE,
    requested_url TEXT NOT NULL,
    final_url TEXT,
    started_ts INTEGER NOT NULL,
    finished_ts INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
    http_status INTEGER,
    source_item_count INTEGER NOT NULL DEFAULT 0,
    parsed_post_count INTEGER NOT NULL DEFAULT 0,
    failed_item_count INTEGER NOT NULL DEFAULT 0,
    inserted_posts INTEGER NOT NULL DEFAULT 0,
    updated_posts INTEGER NOT NULL DEFAULT 0,
    inserted_account_posts INTEGER NOT NULL DEFAULT 0,
    updated_account_posts INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    FOREIGN KEY (account_username) REFERENCES accounts(username) ON DELETE CASCADE
);

CREATE INDEX idx_posts_published_ts
ON posts(published_ts DESC, post_id DESC);

CREATE INDEX idx_account_posts_post_id
ON account_posts(post_id, account_username);

CREATE INDEX idx_fetch_runs_account_started_ts
ON fetch_runs(account_username, started_ts DESC);
"""


class SchemaError(RuntimeError):
    pass


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)


class SQLiteStorage:
    def __init__(self, db_path: str | Path = "data/data.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 5000")
        self._ensure_schema()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SQLiteStorage":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _ensure_schema(self) -> None:
        tables = {
            row["name"]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if not tables:
            create_schema(self.conn)
            self.conn.commit()
            return
        if "schema_version" not in tables:
            raise SchemaError("Unversioned database detected; this build requires a v2 database")

        row = self.conn.execute("SELECT version FROM schema_version WHERE singleton = 1").fetchone()
        version = int(row["version"]) if row else None
        if version != SCHEMA_VERSION:
            raise SchemaError(f"Unsupported database schema version: {version!r}; expected {SCHEMA_VERSION}")
        missing_tables = REQUIRED_TABLES - tables
        if missing_tables:
            raise SchemaError(f"Database schema is incomplete; missing tables: {', '.join(sorted(missing_tables))}")

    def save_feed(
        self,
        feed: ParsedFeed,
        *,
        requested_url: str,
        final_url: str,
        started_ts: int,
        finished_ts: int,
        http_status: int,
    ) -> StorageStats:
        counters = {
            "inserted_posts": 0,
            "updated_posts": 0,
            "inserted_account_posts": 0,
            "updated_account_posts": 0,
            "inserted_source_items": 0,
            "updated_source_items": 0,
        }

        self.conn.execute("BEGIN")
        try:
            self._upsert_account(
                feed.username,
                display_name=feed.display_name,
                source="nitter-rss",
                profile_url=feed.source_url,
                feed_url=final_url,
                checked_ts=finished_ts,
                success=True,
            )
            for feed_post in feed.posts:
                post_change = self._upsert_post(feed_post, seen_ts=finished_ts)
                account_post_change = self._upsert_account_post(feed_post, seen_ts=finished_ts)
                source_item_change = self._upsert_source_item(feed_post, seen_ts=finished_ts)
                if post_change:
                    counters[f"{post_change}_posts"] += 1
                if account_post_change:
                    counters[f"{account_post_change}_account_posts"] += 1
                if source_item_change:
                    counters[f"{source_item_change}_source_items"] += 1

            total_posts, last_post_id, last_post_ts = self._refresh_account_stats(feed.username, finished_ts)
            self._insert_fetch_run(
                account_username=feed.username,
                requested_url=requested_url,
                final_url=final_url,
                started_ts=started_ts,
                finished_ts=finished_ts,
                status="success",
                http_status=http_status,
                source_item_count=feed.source_item_count,
                parsed_post_count=len(feed.posts),
                failed_item_count=feed.failed_item_count,
                inserted_posts=counters["inserted_posts"],
                updated_posts=counters["updated_posts"],
                inserted_account_posts=counters["inserted_account_posts"],
                updated_account_posts=counters["updated_account_posts"],
                error_message=None,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return StorageStats(
            **counters,
            total_account_posts=total_posts,
            last_post_id=last_post_id,
            last_post_ts=last_post_ts,
        )

    def record_fetch_failure(
        self,
        username: str,
        *,
        requested_url: str,
        final_url: str | None,
        started_ts: int,
        finished_ts: int,
        error_message: str,
        http_status: int | None = None,
    ) -> None:
        username = normalize_username(username)
        profile_url = requested_url.removesuffix("/rss")
        self.conn.execute("BEGIN")
        try:
            self._upsert_account(
                username,
                display_name=None,
                source="nitter-rss",
                profile_url=profile_url,
                feed_url=requested_url,
                checked_ts=finished_ts,
                success=False,
            )
            self._insert_fetch_run(
                account_username=username,
                requested_url=requested_url,
                final_url=final_url,
                started_ts=started_ts,
                finished_ts=finished_ts,
                status="failed",
                http_status=http_status,
                source_item_count=0,
                parsed_post_count=0,
                failed_item_count=0,
                inserted_posts=0,
                updated_posts=0,
                inserted_account_posts=0,
                updated_account_posts=0,
                error_message=error_message,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def _upsert_account(
        self,
        username: str,
        *,
        display_name: str | None,
        source: str,
        profile_url: str | None,
        feed_url: str,
        checked_ts: int,
        success: bool,
    ) -> None:
        username = normalize_username(username)
        self.conn.execute(
            """
            INSERT INTO accounts(
                username, display_name, source, profile_url, feed_url,
                last_checked_ts, last_success_ts, created_ts, updated_ts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                display_name = COALESCE(excluded.display_name, accounts.display_name),
                source = excluded.source,
                profile_url = COALESCE(excluded.profile_url, accounts.profile_url),
                feed_url = excluded.feed_url,
                last_checked_ts = excluded.last_checked_ts,
                last_success_ts = COALESCE(excluded.last_success_ts, accounts.last_success_ts),
                updated_ts = excluded.updated_ts
            """,
            (
                username,
                display_name,
                source,
                profile_url,
                feed_url,
                checked_ts,
                checked_ts if success else None,
                checked_ts,
                checked_ts,
            ),
        )

    @staticmethod
    def _post_values(post: Post) -> tuple:
        referenced = post.referenced_post
        return (
            post.author_username,
            post.kind,
            post.content_text,
            post.content_html,
            post.url,
            post.published_ts,
            referenced.post_id if referenced else None,
            referenced.author_username if referenced else None,
            referenced.content_text if referenced else None,
            referenced.url if referenced else None,
        )

    def _upsert_post(self, feed_post: FeedPost, *, seen_ts: int) -> str | None:
        post = feed_post.post
        existing = self.conn.execute(
            """
            SELECT author_username, kind, content_text, content_html, url, published_ts,
                   referenced_post_id, referenced_author_username, referenced_content_text, referenced_url
            FROM posts WHERE post_id = ?
            """,
            (post.post_id,),
        ).fetchone()
        values = self._post_values(post)

        if existing is None:
            self.conn.execute(
                """
                INSERT INTO posts(
                    post_id, author_username, kind, content_text, content_html, url, published_ts,
                    referenced_post_id, referenced_author_username, referenced_content_text, referenced_url,
                    first_seen_ts, last_seen_ts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (post.post_id, *values, seen_ts, seen_ts),
            )
            return "inserted"

        if feed_post.relationship == "reposted" and existing["kind"] in {"reply", "quote"}:
            values = (
                values[0],
                existing["kind"],
                values[2],
                values[3],
                values[4],
                values[5],
                existing["referenced_post_id"],
                existing["referenced_author_username"],
                existing["referenced_content_text"],
                existing["referenced_url"],
            )

        existing_values = tuple(existing)
        if existing_values != values:
            self.conn.execute(
                """
                UPDATE posts SET
                    author_username = ?, kind = ?, content_text = ?, content_html = ?, url = ?, published_ts = ?,
                    referenced_post_id = ?, referenced_author_username = ?, referenced_content_text = ?,
                    referenced_url = ?, last_seen_ts = ?
                WHERE post_id = ?
                """,
                (*values, seen_ts, post.post_id),
            )
            return "updated"

        self.conn.execute("UPDATE posts SET last_seen_ts = ? WHERE post_id = ?", (seen_ts, post.post_id))
        return None

    def _upsert_account_post(self, feed_post: FeedPost, *, seen_ts: int) -> str | None:
        values = (feed_post.relationship, feed_post.feed_title, feed_post.source_url, feed_post.guid)
        existing = self.conn.execute(
            """
            SELECT relationship, feed_title, source_url, guid
            FROM account_posts WHERE account_username = ? AND post_id = ?
            """,
            (feed_post.account_username, feed_post.post.post_id),
        ).fetchone()
        if existing is None:
            self.conn.execute(
                """
                INSERT INTO account_posts(
                    account_username, post_id, relationship, feed_title, source_url, guid,
                    first_seen_ts, last_seen_ts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feed_post.account_username,
                    feed_post.post.post_id,
                    *values,
                    seen_ts,
                    seen_ts,
                ),
            )
            return "inserted"

        if tuple(existing) != values:
            self.conn.execute(
                """
                UPDATE account_posts SET
                    relationship = ?, feed_title = ?, source_url = ?, guid = ?, last_seen_ts = ?
                WHERE account_username = ? AND post_id = ?
                """,
                (*values, seen_ts, feed_post.account_username, feed_post.post.post_id),
            )
            return "updated"

        self.conn.execute(
            """
            UPDATE account_posts SET last_seen_ts = ?
            WHERE account_username = ? AND post_id = ?
            """,
            (seen_ts, feed_post.account_username, feed_post.post.post_id),
        )
        return None

    def _upsert_source_item(self, feed_post: FeedPost, *, seen_ts: int) -> str | None:
        if feed_post.raw_xml is None:
            return None
        content_hash = hashlib.sha256(feed_post.raw_xml.encode("utf-8")).hexdigest()
        existing = self.conn.execute(
            """
            SELECT content_hash FROM source_items
            WHERE account_username = ? AND post_id = ?
            """,
            (feed_post.account_username, feed_post.post.post_id),
        ).fetchone()
        if existing is None:
            self.conn.execute(
                """
                INSERT INTO source_items(
                    account_username, post_id, content_hash, raw_xml, created_ts, updated_ts
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    feed_post.account_username,
                    feed_post.post.post_id,
                    content_hash,
                    feed_post.raw_xml,
                    seen_ts,
                    seen_ts,
                ),
            )
            return "inserted"
        if existing["content_hash"] == content_hash:
            return None

        self.conn.execute(
            """
            UPDATE source_items SET content_hash = ?, raw_xml = ?, updated_ts = ?
            WHERE account_username = ? AND post_id = ?
            """,
            (
                content_hash,
                feed_post.raw_xml,
                seen_ts,
                feed_post.account_username,
                feed_post.post.post_id,
            ),
        )
        return "updated"

    def _refresh_account_stats(self, username: str, checked_ts: int) -> tuple[int, str | None, int | None]:
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS total_posts
            FROM account_posts
            WHERE account_username = ?
            """,
            (username,),
        ).fetchone()
        latest = self.conn.execute(
            """
            SELECT p.post_id, p.published_ts
            FROM account_posts ap
            JOIN posts p ON p.post_id = ap.post_id
            WHERE ap.account_username = ?
            ORDER BY p.published_ts DESC, p.post_id DESC
            LIMIT 1
            """,
            (username,),
        ).fetchone()
        total_posts = int(row["total_posts"] or 0)
        last_post_id = latest["post_id"] if latest else None
        last_post_ts = latest["published_ts"] if latest else None
        self.conn.execute(
            """
            UPDATE accounts SET
                total_posts = ?, last_post_id = ?, last_post_ts = ?, updated_ts = ?
            WHERE username = ?
            """,
            (total_posts, last_post_id, last_post_ts, checked_ts, username),
        )
        return total_posts, last_post_id, last_post_ts

    def _insert_fetch_run(self, **values) -> None:
        self.conn.execute(
            """
            INSERT INTO fetch_runs(
                account_username, requested_url, final_url, started_ts, finished_ts, status,
                http_status, source_item_count, parsed_post_count, failed_item_count,
                inserted_posts, updated_posts, inserted_account_posts, updated_account_posts,
                error_message
            )
            VALUES (
                :account_username, :requested_url, :final_url, :started_ts, :finished_ts, :status,
                :http_status, :source_item_count, :parsed_post_count, :failed_item_count,
                :inserted_posts, :updated_posts, :inserted_account_posts, :updated_account_posts,
                :error_message
            )
            """,
            values,
        )

    @staticmethod
    def _decode_post(row: sqlite3.Row) -> FeedPost:
        referenced_post = None
        if any(
            row[key]
            for key in (
                "referenced_post_id",
                "referenced_author_username",
                "referenced_content_text",
                "referenced_url",
            )
        ):
            referenced_post = ReferencedPost(
                post_id=row["referenced_post_id"],
                author_username=row["referenced_author_username"],
                content_text=row["referenced_content_text"],
                url=row["referenced_url"],
            )
        return FeedPost(
            account_username=row["account_username"],
            account_display_name=row["account_display_name"],
            relationship=cast(AccountPostRelationship, row["relationship"]),
            feed_title=row["feed_title"],
            source_url=row["source_url"],
            guid=row["guid"],
            first_seen_ts=row["first_seen_ts"],
            last_seen_ts=row["last_seen_ts"],
            post=Post(
                post_id=row["post_id"],
                author_username=row["author_username"],
                kind=cast(PostKind, row["kind"]),
                content_text=row["content_text"],
                content_html=row["content_html"],
                url=row["url"],
                published_ts=row["published_ts"],
                referenced_post=referenced_post,
            ),
        )

    @staticmethod
    def _query_sql(account_filter: str) -> str:
        return f"""
            SELECT
                ap.account_username,
                a.display_name AS account_display_name,
                ap.relationship,
                ap.feed_title,
                ap.source_url,
                ap.guid,
                ap.first_seen_ts,
                ap.last_seen_ts,
                p.post_id,
                p.author_username,
                p.kind,
                p.content_text,
                p.content_html,
                p.url,
                p.published_ts,
                p.referenced_post_id,
                p.referenced_author_username,
                p.referenced_content_text,
                p.referenced_url
            FROM account_posts ap
            JOIN accounts a ON a.username = ap.account_username
            JOIN posts p ON p.post_id = ap.post_id
            WHERE {account_filter}
              AND p.published_ts >= ?
              AND p.published_ts < ?
            ORDER BY p.published_ts ASC, p.post_id ASC, ap.account_username ASC
            LIMIT ?
        """

    def query_posts(self, username: str, *, start_ts: int, end_ts: int, limit: int = 200) -> list[FeedPost]:
        rows = self.conn.execute(
            self._query_sql("ap.account_username = ?"),
            (normalize_username(username), start_ts, end_ts, max(limit, 1)),
        ).fetchall()
        return [self._decode_post(row) for row in rows]

    def query_posts_for_accounts(
        self,
        accounts: list[str],
        *,
        start_ts: int,
        end_ts: int,
        limit: int = 500,
    ) -> list[FeedPost]:
        normalized_accounts = list(dict.fromkeys(normalize_username(account) for account in accounts if account.strip()))
        if not normalized_accounts:
            return []
        placeholders = ",".join("?" for _ in normalized_accounts)
        rows = self.conn.execute(
            self._query_sql(f"ap.account_username IN ({placeholders})"),
            (*normalized_accounts, start_ts, end_ts, max(limit, 1)),
        ).fetchall()
        return [self._decode_post(row) for row in rows]
