# Advanced CLI

Read this reference only for machine-readable output, non-default paths, or
fetch tuning.

## Machine-readable output

Use `--json` for queries:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss query elonmusk --start 2026-03-07 --end 2026-03-08 --json
uv run --directory {SKILL_DIR} twitter-x-rss query-faction musk --start 2026-03-07 --end 2026-03-08 --json
```

Use `--print-json` for updates. It emits one JSON document containing the
sync summary and the posts parsed from that fetch:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss update elonmusk --print-json
uv run --directory {SKILL_DIR} twitter-x-rss update-faction musk --print-json
```

On a machine-readable failure, the CLI emits a JSON error object and exits
non-zero. Account queries default to 200 posts; faction queries default to
500. Set `--limit` when a smaller or larger result set is appropriate.

## Custom paths

Use these for isolated tests or data outside the default database/config:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss query elonmusk \
  --db-path /tmp/twitter-x-rss.db \
  --start 2026-03-07

uv run --directory {SKILL_DIR} twitter-x-rss update-faction musk \
  --factions-path /tmp/factions.json \
  --db-path /tmp/twitter-x-rss.db
```

## Fetch settings

Keep the defaults unless the user is explicitly tuning a known RSS endpoint:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss update elonmusk --base-url https://nitter.net
uv run --directory {SKILL_DIR} twitter-x-rss update-faction musk --concurrency 4
uv run --directory {SKILL_DIR} twitter-x-rss update-faction musk \
  --request-delay-min 1.2 \
  --request-delay-max 1.5
```

Faction request delays apply globally between request starts, including when
concurrency is greater than one.
