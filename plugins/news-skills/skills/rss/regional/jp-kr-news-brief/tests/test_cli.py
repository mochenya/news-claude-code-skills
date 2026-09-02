from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import json

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import cli.main as cli_main


class TimeWindowArgumentTests(unittest.TestCase):
    def test_fetch_accepts_since_and_until(self) -> None:
        parser = cli_main.build_parser()

        args = parser.parse_args(
            [
                "fetch",
                "--all",
                "--since",
                "2026-07-16T08:00:00+08:00",
                "--until",
                "2026-07-16T12:00:00+08:00",
            ]
        )

        self.assertEqual(args.since, "2026-07-16T08:00:00+08:00")
        self.assertEqual(args.until, "2026-07-16T12:00:00+08:00")
        self.assertIsNone(args.limit)

    def test_fetch_requires_a_complete_time_window(self) -> None:
        parser = cli_main.build_parser()
        stderr = StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            parser.parse_args(
                ["fetch", "--all", "--until", "2026-07-16T12:00:00+08:00"]
            )

        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            parser.parse_args(
                ["fetch", "--all", "--since", "2026-07-16T08:00:00+08:00"]
            )

    def test_fetch_without_limit_scans_the_full_feed(self) -> None:
        source = {"key": "test", "name": "Test Feed", "url": "https://example.com/rss"}
        entries = [
            cli_main.feedparser.FeedParserDict(
                title=f"item-{index}",
                link=f"https://example.com/{index}",
                description="",
                published="Thu, 16 Jul 2026 01:00:00 GMT",
            )
            for index in range(12)
        ]
        feed = SimpleNamespace(bozo=False, entries=entries)

        with patch.object(cli_main.feedparser, "parse", return_value=feed):
            result = cli_main._fetch_one(source, limit=None)

        self.assertEqual(len(result), 12)

    def test_rfc2822_colon_timezone_is_converted_to_bjt(self) -> None:
        source = {"key": "test", "name": "Test Feed", "url": "https://example.com/rss"}
        entry = cli_main.feedparser.FeedParserDict(
            title="timezone-aware item",
            link="https://example.com/timezone-aware",
            description="",
            published="Sun, 19 Jul 2026 17:05:58 +09:00",
        )
        feed = SimpleNamespace(bozo=False, entries=[entry])

        with patch.object(cli_main.feedparser, "parse", return_value=feed):
            result = cli_main._fetch_one(source, limit=None)

        self.assertEqual(result[0]["published_bjt"], "2026-07-19T16:05:58+08:00")

    def test_time_window_is_start_inclusive_and_end_exclusive(self) -> None:
        filter_fn = getattr(cli_main, "_filter_by_time_window", None)
        self.assertIsNotNone(filter_fn, "time-window filtering is not implemented")
        entries = [
            {"title": "before", "published_bjt": "2026-07-16T07:59:59+08:00"},
            {"title": "at-start", "published_bjt": "2026-07-16T08:00:00+08:00"},
            {"title": "inside", "published_bjt": "2026-07-16T11:59:59+08:00"},
            {"title": "at-end", "published_bjt": "2026-07-16T12:00:00+08:00"},
            {"title": "undated", "published_bjt": ""},
        ]

        result = filter_fn(
            entries,
            since="2026-07-16T08:00:00+08:00",
            until="2026-07-16T12:00:00+08:00",
        )

        self.assertEqual([item["title"] for item in result], ["at-start", "inside"])

    def test_fetch_applies_time_window_before_json_output(self) -> None:
        args = Namespace(
            source=None,
            limit=10,
            format="json",
            since="2026-07-16T08:00:00+08:00",
            until="2026-07-16T12:00:00+08:00",
        )
        source = {"key": "test", "name": "Test Feed", "url": "https://example.com/rss"}
        fetched = [
            {
                "source_name": "Test Feed",
                "source_key": "test",
                "title": "outside",
                "link": "https://example.com/outside",
                "description": "",
                "published_bjt": "2026-07-16T07:59:59+08:00",
            },
            {
                "source_name": "Test Feed",
                "source_key": "test",
                "title": "inside",
                "link": "https://example.com/inside",
                "description": "",
                "published_bjt": "2026-07-16T09:00:00+08:00",
            },
        ]
        stdout = StringIO()
        stderr = StringIO()

        with (
            patch.object(cli_main, "load_sources", return_value=[source]),
            patch.object(cli_main, "_fetch_one", return_value=fetched),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = cli_main.cmd_fetch(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual([item["title"] for item in json.loads(stdout.getvalue())], ["inside"])


if __name__ == "__main__":
    unittest.main()
