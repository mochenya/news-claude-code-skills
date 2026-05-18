# Advanced CLI

Use these options only when the basic commands are not enough.

## Parseable output

Add `--json` to query commands when a script needs structured data:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss query elonmusk --start 2026-03-07 --end 2026-03-08 --json
uv run --directory {SKILL_DIR} twitter-x-rss query-faction musk --start 2026-03-07 --end 2026-03-08 --json
```

## Print fetched posts during update

Update commands already print a summary. Add `--print-json` to also print parsed posts:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss update elonmusk --print-json
uv run --directory {SKILL_DIR} twitter-x-rss update-faction musk --print-json
```

## Custom paths

Use these when testing or keeping data outside the default `data/` folder:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss query elonmusk \
  --db-path /tmp/rss.db \
  --start 2026-03-07

uv run --directory {SKILL_DIR} twitter-x-rss update-faction musk \
  --factions-path /tmp/factions.json \
  --data-dir /tmp/rss-data
```

## Fetch settings

```bash
uv run --directory {SKILL_DIR} twitter-x-rss update-faction musk --concurrency 8
uv run --directory {SKILL_DIR} twitter-x-rss update elonmusk --base-url https://nitter.net
uv run --directory {SKILL_DIR} twitter-x-rss update elonmusk --dump-feed
uv run --directory {SKILL_DIR} twitter-x-rss update elonmusk --no-json-archive
```

- `--concurrency`: number of faction accounts fetched at once. Default is `4`.
- `--base-url`: Nitter-compatible host.
- `--dump-feed`: save raw RSS XML for debugging.
- `--no-json-archive`: write SQLite only, skip per-user JSON archive files.
