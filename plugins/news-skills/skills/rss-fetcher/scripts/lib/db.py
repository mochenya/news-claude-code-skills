from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Mapping, Sequence

from .source_registry import CategoryConfig

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "news.db"

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS categories (
      id INTEGER PRIMARY KEY,
      category_key TEXT NOT NULL UNIQUE,
      category_name TEXT NOT NULL,
      enabled INTEGER NOT NULL DEFAULT 1,
      sort_order INTEGER NOT NULL DEFAULT 0,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feeds (
      id INTEGER PRIMARY KEY,
      feed_url TEXT NOT NULL UNIQUE,
      feed_title TEXT,
      site_url TEXT,
      etag TEXT,
      modified TEXT,
      last_checked_at INTEGER,
      last_success_at INTEGER,
      last_status TEXT,
      last_error TEXT,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sources (
      id INTEGER PRIMARY KEY,
      source_key TEXT NOT NULL UNIQUE,
      category_id INTEGER NOT NULL,
      feed_id INTEGER NOT NULL,
      source_name TEXT NOT NULL,
      enabled INTEGER NOT NULL DEFAULT 1,
      sort_order INTEGER NOT NULL DEFAULT 0,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL,
      FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
      FOREIGN KEY (feed_id) REFERENCES feeds(id) ON DELETE RESTRICT,
      UNIQUE(category_id, feed_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entries (
      id INTEGER PRIMARY KEY,
      feed_id INTEGER NOT NULL,
      entry_key TEXT NOT NULL,
      guid_raw TEXT,
      link TEXT,
      title TEXT NOT NULL DEFAULT '',
      description_text TEXT NOT NULL DEFAULT '',
      author TEXT,
      published_ts INTEGER,
      published_iso_bjt TEXT,
      raw_published TEXT,
      content_hash TEXT NOT NULL,
      first_seen_at INTEGER NOT NULL,
      last_seen_at INTEGER NOT NULL,
      fetched_at INTEGER NOT NULL,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL,
      FOREIGN KEY (feed_id) REFERENCES feeds(id) ON DELETE RESTRICT,
      UNIQUE(feed_id, entry_key)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_sources_category_order ON sources(category_id, enabled, sort_order, id)",
    "CREATE INDEX IF NOT EXISTS idx_sources_feed ON sources(feed_id)",
    "CREATE INDEX IF NOT EXISTS idx_entries_feed_published ON entries(feed_id, published_ts DESC, id DESC)",
    "CREATE INDEX IF NOT EXISTS idx_entries_published ON entries(published_ts DESC, id DESC)",
    "CREATE INDEX IF NOT EXISTS idx_entries_link ON entries(link)",
    "CREATE INDEX IF NOT EXISTS idx_entries_last_seen ON entries(last_seen_at DESC, id DESC)",
)


def get_db_path(path: str | Path | None = None) -> Path:
    return Path(path) if path else DB_PATH


def connect_db(path: str | Path | None = None) -> sqlite3.Connection:
    db_path = get_db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)
    conn.commit()


def current_timestamp() -> int:
    return int(time.time())


def sync_registry(conn: sqlite3.Connection, categories: Sequence[CategoryConfig]) -> None:
    now = current_timestamp()
    category_keys = {category.key for category in categories}
    source_keys = {source.key for category in categories for source in category.sources}

    for category in categories:
        category_id = upsert_category(conn, category, now)
        for source in category.sources:
            feed_id = upsert_feed(conn, source.url, now)
            upsert_source(conn, category_id, feed_id, source, now)

    if category_keys:
        placeholders = ", ".join("?" for _ in category_keys)
        conn.execute(
            f"UPDATE categories SET enabled = 0, updated_at = ? WHERE category_key NOT IN ({placeholders})",
            (now, *sorted(category_keys)),
        )
    else:
        conn.execute("UPDATE categories SET enabled = 0, updated_at = ?", (now,))

    if source_keys:
        placeholders = ", ".join("?" for _ in source_keys)
        conn.execute(
            f"UPDATE sources SET enabled = 0, updated_at = ? WHERE source_key NOT IN ({placeholders})",
            (now, *sorted(source_keys)),
        )
    else:
        conn.execute("UPDATE sources SET enabled = 0, updated_at = ?", (now,))

    conn.commit()


def upsert_category(conn: sqlite3.Connection, category: CategoryConfig, now: int) -> int:
    conn.execute(
        """
        INSERT INTO categories (category_key, category_name, enabled, sort_order, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(category_key) DO UPDATE SET
          category_name = excluded.category_name,
          enabled = excluded.enabled,
          sort_order = excluded.sort_order,
          updated_at = excluded.updated_at
        """,
        (category.key, category.name, int(category.enabled), category.sort_order, now, now),
    )
    row = conn.execute("SELECT id FROM categories WHERE category_key = ?", (category.key,)).fetchone()
    if row is None:
        raise RuntimeError(f"failed to upsert category: {category.key}")
    return int(row["id"])


def upsert_feed(conn: sqlite3.Connection, feed_url: str, now: int) -> int:
    conn.execute(
        """
        INSERT INTO feeds (feed_url, created_at, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(feed_url) DO UPDATE SET
          updated_at = excluded.updated_at
        """,
        (feed_url, now, now),
    )
    row = conn.execute("SELECT id FROM feeds WHERE feed_url = ?", (feed_url,)).fetchone()
    if row is None:
        raise RuntimeError(f"failed to upsert feed: {feed_url}")
    return int(row["id"])


def upsert_source(conn: sqlite3.Connection, category_id: int, feed_id: int, source, now: int) -> int:
    conn.execute(
        """
        INSERT INTO sources (source_key, category_id, feed_id, source_name, enabled, sort_order, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_key) DO UPDATE SET
          category_id = excluded.category_id,
          feed_id = excluded.feed_id,
          source_name = excluded.source_name,
          enabled = excluded.enabled,
          sort_order = excluded.sort_order,
          updated_at = excluded.updated_at
        """,
        (source.key, category_id, feed_id, source.name, int(source.enabled), source.sort_order, now, now),
    )
    row = conn.execute("SELECT id FROM sources WHERE source_key = ?", (source.key,)).fetchone()
    if row is None:
        raise RuntimeError(f"failed to upsert source: {source.key}")
    return int(row["id"])


def update_feed_fetch_status(
    conn: sqlite3.Connection,
    feed_id: int,
    *,
    last_checked_at: int,
    feed_title: str | None = None,
    site_url: str | None = None,
    etag: str | None = None,
    modified: str | None = None,
    last_success_at: int | None = None,
    last_status: str | None = None,
    last_error: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE feeds
        SET feed_title = COALESCE(?, feed_title),
            site_url = COALESCE(?, site_url),
            etag = ?,
            modified = ?,
            last_checked_at = ?,
            last_success_at = COALESCE(?, last_success_at),
            last_status = ?,
            last_error = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            empty_to_none(feed_title),
            empty_to_none(site_url),
            empty_to_none(etag),
            empty_to_none(modified),
            last_checked_at,
            last_success_at,
            last_status,
            last_error,
            last_checked_at,
            feed_id,
        ),
    )


def upsert_entry(conn: sqlite3.Connection, payload: Mapping[str, object]) -> str:
    existing = conn.execute(
        "SELECT id, content_hash, first_seen_at FROM entries WHERE feed_id = ? AND entry_key = ?",
        (payload["feed_id"], payload["entry_key"]),
    ).fetchone()

    if existing is None:
        conn.execute(
            """
            INSERT INTO entries (
              feed_id, entry_key, guid_raw, link, title, description_text, author,
              published_ts, published_iso_bjt, raw_published, content_hash,
              first_seen_at, last_seen_at, fetched_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["feed_id"],
                payload["entry_key"],
                payload.get("guid_raw"),
                payload.get("link"),
                payload.get("title", ""),
                payload.get("description_text", ""),
                payload.get("author"),
                payload.get("published_ts"),
                payload.get("published_iso_bjt"),
                payload.get("raw_published"),
                payload["content_hash"],
                payload["fetched_at"],
                payload["fetched_at"],
                payload["fetched_at"],
                payload["fetched_at"],
                payload["fetched_at"],
            ),
        )
        return "inserted"

    if existing["content_hash"] == payload["content_hash"]:
        conn.execute(
            """
            UPDATE entries
            SET last_seen_at = ?,
                fetched_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (payload["fetched_at"], payload["fetched_at"], payload["fetched_at"], existing["id"]),
        )
        return "unchanged"

    conn.execute(
        """
        UPDATE entries
        SET guid_raw = ?,
            link = ?,
            title = ?,
            description_text = ?,
            author = ?,
            published_ts = ?,
            published_iso_bjt = ?,
            raw_published = ?,
            content_hash = ?,
            last_seen_at = ?,
            fetched_at = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload.get("guid_raw"),
            payload.get("link"),
            payload.get("title", ""),
            payload.get("description_text", ""),
            payload.get("author"),
            payload.get("published_ts"),
            payload.get("published_iso_bjt"),
            payload.get("raw_published"),
            payload["content_hash"],
            payload["fetched_at"],
            payload["fetched_at"],
            payload["fetched_at"],
            existing["id"],
        ),
    )
    return "updated"


def get_category_rows(conn: sqlite3.Connection, *, include_disabled: bool = False) -> list[sqlite3.Row]:
    sql = "SELECT * FROM categories"
    params: list[object] = []
    if not include_disabled:
        sql += " WHERE enabled = 1"
    sql += " ORDER BY sort_order ASC, category_key ASC"
    return list(conn.execute(sql, params))


def get_feed_rows_for_sync(conn: sqlite3.Connection, category_key: str | None = None) -> list[sqlite3.Row]:
    params: list[object] = []
    sql = """
        SELECT DISTINCT f.*
        FROM feeds f
        JOIN sources s ON s.feed_id = f.id
        JOIN categories c ON c.id = s.category_id
        WHERE c.enabled = 1 AND s.enabled = 1
    """
    if category_key:
        sql += " AND c.category_key = ?"
        params.append(category_key)
    sql += " ORDER BY f.feed_url ASC"
    return list(conn.execute(sql, params))


def get_category_query_rows(
    conn: sqlite3.Connection,
    category_key: str,
    *,
    limit: int | None = None,
    since_ts: int | None = None,
    until_ts: int | None = None,
) -> tuple[sqlite3.Row | None, list[sqlite3.Row]]:
    category = conn.execute(
        "SELECT * FROM categories WHERE category_key = ? AND enabled = 1",
        (category_key,),
    ).fetchone()
    if category is None:
        return None, []

    sql = """
        SELECT
          e.id,
          s.source_name,
          e.title,
          e.link,
          e.description_text,
          e.published_ts,
          e.published_iso_bjt
        FROM entries e
        JOIN sources s ON s.feed_id = e.feed_id
        JOIN categories c ON c.id = s.category_id
        WHERE c.category_key = ?
          AND c.enabled = 1
          AND s.enabled = 1
          AND e.published_ts IS NOT NULL
    """
    params: list[object] = [category_key]
    if since_ts is not None:
        sql += " AND e.published_ts >= ?"
        params.append(since_ts)
    if until_ts is not None:
        sql += " AND e.published_ts < ?"
        params.append(until_ts)
    sql += " ORDER BY e.published_ts DESC, e.id DESC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    rows = list(conn.execute(sql, params))
    return category, rows


def empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None
