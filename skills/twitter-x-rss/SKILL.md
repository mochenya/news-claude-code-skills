---
name: twitter-x-rss
description: Use the local twitter-x-rss CLI to update and query X/Nitter RSS posts by account or faction. Trigger this skill when the user asks for local X/Twitter RSS collection, faction updates, faction queries, or checking posts from configured account groups.
---

# Twitter X RSS

Use this skill's CLI to collect and query local Twitter/X RSS data.

Run commands from this skill environment:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss <command>
```

The default output is made for terminal reading. Only add `--json` when another script needs to parse the result.

## Common commands

Update one account:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss update <username>
```

Query one account:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss query <username> --start <start> --end <end>
```

Update one faction:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss update-faction <faction>
```

Query one faction:

```bash
uv run --directory {SKILL_DIR} twitter-x-rss query-faction <faction> --start <start> --end <end>
```

## Useful examples

```bash
uv run --directory {SKILL_DIR} twitter-x-rss update elonmusk
uv run --directory {SKILL_DIR} twitter-x-rss query elonmusk --start 2026-03-07 --end 2026-03-08
uv run --directory {SKILL_DIR} twitter-x-rss update-faction musk
uv run --directory {SKILL_DIR} twitter-x-rss query-faction musk --start "2026-03-07 09:00" --end "2026-03-07 12:00"
```

## Time formats

These formats work:

```text
2026-03-07
2026-03-07 09:00
2026-03-07 09:00:30
1772812800
2026-03-07T09:00:00+08:00
2026-03-07T01:00:00Z
```

## References

Read these only when needed:

- `references/factions-json.md` — how to write `config/factions.json`
- `references/advanced-cli.md` — less common CLI options

## Notes

- Factions are defined in `config/factions.json`.
- Local data is stored under `{SKILL_DIR}/data/` by default.
- If a query returns no rows, run the matching update command first, then query again.
