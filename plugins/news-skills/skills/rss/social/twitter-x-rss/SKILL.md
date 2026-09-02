---
name: twitter-x-rss
description: Use when monitoring configured X factions or handles. Retains the legacy name but uses the local xfactions CLI and SQLite only.
allowed-tools: Bash(/home/lht/.local/bin/xfactions *)
---

# X Faction Monitor (xfactions backend)

This skill retains the `twitter-x-rss` name only for compatibility with existing workflows. The old RSS client, `uv run ... twitter-x-rss` commands, its SQLite database, and direct RSS URLs are retired. All operational reads and writes use `xfactions`.

## Runtime authority

```bash
XF=/home/lht/.local/bin/xfactions
DB=/home/lht/.config/xfactions/xfactions.db
```

- The `xfactions` database is the runtime authority for watched users, faction/group memberships, posts, and sync checkpoints.
- The historical `config/factions.json` was a one-time import source. Do not load it for normal operations and do not infer current membership from it.
- Use an explicit `--db "$DB"` on every command.
- Do not query SQLite directly and do not call FxEmbed directly.

## Route requests

1. Resolve the target as a handle, faction, or faction/group membership with `watch list` when unclear.
2. Interpret report windows in `Asia/Shanghai`, then convert to UTC RFC3339. All post queries use half-open `[from, to)` intervals.
3. When freshness is requested outside the scheduled launcher, run `sync` before `query posts`.
4. The four-faction scheduled launcher performs all `sync` calls before starting the Agent. In that job, read `XFACTIONS_SYNC_DIR` and query only; do not start another sync.
5. When the request is explicitly for already-collected/local data, skip `sync` and query only.
6. An empty `query posts` result means no locally collected posts matched the window; it is not proof that the account did not post.

## Core commands

```bash
# Inspect active monitored accounts and memberships
$XF --db "$DB" watch list

# Refresh one handle or one faction. The scheduled four-faction launcher uses 8.
$XF --db "$DB" sync --user <handle>
$XF --db "$DB" sync --faction <faction> --concurrency 8 --user-timeout 30
$XF --db "$DB" sync --faction <faction> --group <group>

# Inspect checkpoints and failed accounts
$XF --db "$DB" sync status

# Query local posts. --output ndjson is preferred for downstream filtering.
$XF --db "$DB" query posts --faction <faction> \
  --from <UTC_RFC3339> --to <UTC_RFC3339> --output ndjson
$XF --db "$DB" query posts --user <handle> \
  --from <UTC_RFC3339> --to <UTC_RFC3339> --output ndjson
```

## Result handling

- Check the process exit code and JSON envelope `ok`/`errors` for every command.
- For `sync`, also require `data.failed == 0` before describing a collection as complete. Inspect `data.users[].error` on partial failure.
- In NDJSON, each post is one line and the final line is the summary envelope. Do not summarize that final line as a post.
- First sync stores only the newest provider timeline page. The collection is not a full historical archive.
- For a partial sync, report usable local data as partial and name affected accounts; never relabel it as “无新增”.

## Output format for faction briefs

Use the legacy faction-brief Markdown template, not a JSON object: `🐦` title → `📊` collection window → `📈` monitored faction → `---` → `🧭 要点概览` → numbered thematic sections (`1️⃣`, `2️⃣`) with `📅` Beijing time and `🔗` Markdown source links → `⚠️ 采集状态` → `📊 数据统计` → `**核心观察**`.

For manual delivery, pipe the complete raw Markdown body to `hermes send --to <target> --json`. Do not serialize the brief as `{ "title": ... }`, `{ "text": ... }`, or another JSON envelope.

## Scheduled four-faction morning brief

For `workflows/twitter-four-faction-morning-brief.md`, the shell launcher has already synchronized all factions and exported the exact UTC window plus `XFACTIONS_SYNC_DIR`. Process `musk` → `us_gov` → `indonesia_gov` → `mining` serially: inspect that faction’s collected sync result, query the exported UTC window, then write and send before advancing.

## Boundaries

- This is a best-effort public collection, not an official X archive or complete firehose.
- `owner` is the watched account whose timeline observed a post; the post author can differ for reposts and quotes.
- Do not treat a provider error, a missing local record, or a query result of zero as evidence that an X post was deleted or never existed.
