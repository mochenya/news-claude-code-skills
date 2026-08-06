---
name: twitter-x-rss
description: >-
  Incrementally monitor X/Twitter usernames or configured factions with the
  local twitter-x-rss CLI, then query collected recent posts for summaries.
  Use for requests such as “同步账号/阵营” or “看看某人最近发了什么”. Do not
  use for live/full X search, specific-post lookup, exact-date/history
  retrieval, or official X API actions.
allowed-tools: Bash(uv *)
---

# Twitter/X RSS Monitor

Maintain a local, incremental collection of posts observed from a third-party
RSS mirror. Use it for monitored usernames or configured factions and for
summaries based on posts already collected. Do not present the collection as a
complete X archive or as live search.

## Setup and command prefix

When the environment is missing or dependencies changed, synchronize it once:

```bash
uv sync --directory {SKILL_DIR}
```

Run the CLI with:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss <command>
```

The default output is concise terminal text. Use JSON output when another
command or script must parse the result.

## Route each request

Decline direct-post, exact-date, or complete-history lookups unless the user
explicitly asks for a summary of the local monitoring collection. Explain that
the RSS mirror cannot retrieve missing posts retroactively.

1. Resolve the target as one username or a configured faction. Read
   `config/factions.json` when the faction name or membership is unclear.
2. Resolve the requested window in `Asia/Shanghai`. Use `[start, end)`;
   `--end` defaults to now. Interpret “today” as today at 00:00 through now,
   and “recently” without a window as the latest 24 hours unless the user says
   otherwise.
3. Refresh before reading when the user asks for latest/current/recent posts or
   a daily monitoring update. Use `update` for one username and
   `update-faction` for a configured faction.
4. Query after a successful refresh when the user needs posts to summarize.
   For a local or previously collected window, skip refresh and query directly.
5. Treat an empty query as “no collected posts in this window”, not proof that
   the account posted nothing. If refresh fails or a faction refresh is partial,
   report the failure and do not describe the result as complete.

## Common commands

```bash
uv run --directory {SKILL_DIR} twitter-x-rss update <username>
uv run --directory {SKILL_DIR} twitter-x-rss query <username> --start <start> --end <end>
uv run --directory {SKILL_DIR} twitter-x-rss update-faction <faction>
uv run --directory {SKILL_DIR} twitter-x-rss query-faction <faction> --start <start> --end <end>
```

Updates incrementally store observations in the default SQLite database at
`{SKILL_DIR}/data/data.db`. A query can only return posts that an earlier
update captured; it cannot fetch a missing historical or exact-date post.

## References

Read these only when needed:

- `references/factions-json.md` — faction configuration and validation rules
- `references/advanced-cli.md` — JSON output, custom paths, and fetch tuning
