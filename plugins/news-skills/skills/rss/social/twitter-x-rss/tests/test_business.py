from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from db import SQLiteStorage, SchemaError
from factions import FactionConfig
from parser import parse_rss
from rss_client import RSSResponse
from service import SyncService


def build_rss(
    *,
    account: str,
    creator: str,
    post_id: str,
    title: str,
    description: str,
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>{account.title()} / @{account}</title>
    <link>https://nitter.example/{account}</link>
    <item>
      <title>{title}</title>
      <link>https://nitter.example/{creator}/status/{post_id}#m</link>
      <guid>{post_id}</guid>
      <description><![CDATA[{description}]]></description>
      <dc:creator>@{creator}</dc:creator>
      <pubDate>Wed, 05 Aug 2026 01:02:03 GMT</pubDate>
    </item>
  </channel>
</rss>"""


class DatabaseModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = SQLiteStorage(Path(self.temp_dir.name) / "test.db")

    def tearDown(self) -> None:
        self.storage.close()
        self.temp_dir.cleanup()

    def save(self, xml: str, username: str, seen_ts: int):
        feed_url = f"https://nitter.example/{username}/rss"
        feed = parse_rss(xml, username=username, rss_url=feed_url)
        return self.storage.save_feed(
            feed,
            requested_url=feed_url,
            final_url=feed_url,
            started_ts=seen_ts - 1,
            finished_ts=seen_ts,
            http_status=200,
        )

    def test_one_post_can_belong_to_multiple_accounts(self) -> None:
        direct = build_rss(
            account="xai",
            creator="xai",
            post_id="123456",
            title="A shared post",
            description="A shared post",
        )
        repost = build_rss(
            account="grok",
            creator="xai",
            post_id="123456",
            title="RT by @grok: A shared post",
            description="A shared post",
        )

        first = self.save(direct, "xai", 100)
        second = self.save(repost, "grok", 200)

        self.assertEqual(first.inserted_posts, 1)
        self.assertEqual(second.inserted_posts, 0)
        self.assertEqual(second.inserted_account_posts, 1)
        self.assertEqual(self.storage.conn.execute("SELECT count(*) FROM posts").fetchone()[0], 1)
        self.assertEqual(self.storage.conn.execute("SELECT count(*) FROM account_posts").fetchone()[0], 2)
        self.assertEqual(self.storage.conn.execute("SELECT count(*) FROM source_items").fetchone()[0], 2)

        rows = self.storage.query_posts_for_accounts(
            ["xai", "grok"],
            start_ts=1_700_000_000,
            end_ts=1_900_000_000,
        )
        self.assertEqual([row.display_type for row in rows], ["retweet", "tweet"])
        self.assertEqual({row.account_username for row in rows}, {"grok", "xai"})

    def test_unchanged_item_only_advances_last_seen(self) -> None:
        xml = build_rss(
            account="xai",
            creator="xai",
            post_id="123456",
            title="Stable",
            description="Stable",
        )
        self.save(xml, "xai", 100)
        result = self.save(xml, "xai", 200)

        self.assertEqual(result.inserted_posts, 0)
        self.assertEqual(result.updated_posts, 0)
        self.assertEqual(result.updated_account_posts, 0)
        self.assertEqual(result.updated_source_items, 0)
        last_seen = self.storage.conn.execute(
            "SELECT last_seen_ts FROM account_posts WHERE account_username = 'xai'"
        ).fetchone()[0]
        self.assertEqual(last_seen, 200)

    def test_changed_source_item_updates_raw_and_projection(self) -> None:
        first_xml = build_rss(
            account="xai",
            creator="xai",
            post_id="123456",
            title="Before",
            description="Before",
        )
        second_xml = build_rss(
            account="xai",
            creator="xai",
            post_id="123456",
            title="After",
            description="After",
        )
        self.save(first_xml, "xai", 100)
        result = self.save(second_xml, "xai", 200)

        self.assertEqual(result.updated_posts, 1)
        self.assertEqual(result.updated_account_posts, 1)
        self.assertEqual(result.updated_source_items, 1)
        content = self.storage.conn.execute("SELECT content_text FROM posts").fetchone()[0]
        raw_xml = self.storage.conn.execute("SELECT raw_xml FROM source_items").fetchone()[0]
        self.assertEqual(content, "After")
        self.assertIn("After", raw_xml)

    def test_rejects_unversioned_database(self) -> None:
        unversioned_path = Path(self.temp_dir.name) / "unversioned.db"
        connection = sqlite3.connect(unversioned_path)
        connection.execute("CREATE TABLE old_posts(post_id TEXT PRIMARY KEY)")
        connection.commit()
        connection.close()

        with self.assertRaises(SchemaError):
            SQLiteStorage(unversioned_path)


class _AsyncClientContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeRSSClient:
    def build_rss_url(self, username: str) -> str:
        return f"https://nitter.example/{username}/rss"

    def create_async_client(self) -> _AsyncClientContext:
        return _AsyncClientContext()

    async def fetch_user_rss_async(self, username: str, client=None) -> RSSResponse:
        if username == "broken":
            raise ValueError("unavailable")
        rss_url = self.build_rss_url(username)
        return RSSResponse(
            username=username,
            rss_url=rss_url,
            final_url=rss_url,
            status_code=200,
            content_type="application/rss+xml",
            xml_text=build_rss(
                account=username,
                creator=username,
                post_id="999",
                title="Service post",
                description="Service post",
            ),
        )


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_persists_success_and_failure_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with SQLiteStorage(Path(temp_dir) / "test.db") as storage:
                service = SyncService(storage, _FakeRSSClient())
                results = await service.sync_accounts(
                    ["working", "broken"],
                    concurrency=2,
                    request_delay_min=0,
                    request_delay_max=0,
                )
                self.assertEqual([result.status for result in results], ["success", "failed"])
                runs = storage.conn.execute(
                    "SELECT account_username, status FROM fetch_runs ORDER BY account_username"
                ).fetchall()
                self.assertEqual([tuple(row) for row in runs], [("broken", "failed"), ("working", "success")])


class FactionConfigTests(unittest.TestCase):
    def test_loads_grouped_config_and_rejects_legacy_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "factions.json"
            path.write_text('{"AI": {"groups": {"core": ["@XAI", "grok", "xai"]}}}', encoding="utf-8")
            faction = FactionConfig.load(path).get("ai")
            self.assertEqual(faction.accounts, ["xai", "grok"])

            path.write_text('{"AI": ["xai"]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                FactionConfig.load(path)


if __name__ == "__main__":
    unittest.main()
