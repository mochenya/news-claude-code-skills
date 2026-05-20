---
name: rss-fetcher
description: >-
  Fetch and format news from built-in RSS category collections or a user-provided RSS URL into a Chinese brief.
  Trigger when the user mentions RSS, feed URLs, built-in categories
  (top, world, gov, politics, us, middle-east, russia-ukraine, indonesia, japan, korea, ai),
  or phrases like "抓 RSS", "同步新闻源", "查一下 feed", "fetch rss", "news sync", "news query".
  Not for general web search.
---

# RSS Policy & AI News Brief

Fetch RSS items, then produce a concise, decision-useful Chinese brief focused on politics, government, policy, geopolitics, international affairs, and AI.

## Command selection

Choose the right command based on what the user provides:

| User input | Command | Example |
|---|---|---|
| A direct RSS URL | `news rss <URL>` | `news rss https://example.com/feed.xml` |
| A topic or region name | `news fetch <category>` | `news fetch ai` |
| Needs time-window filtering | `news sync` then `news query` | `news sync us && news query us --since 24h` |
| "All news" or no specific topic | `news fetch --all` | `news fetch --all` |

All commands use the prefix: `uv run --directory {baseDir}`

## Fetch news

### Built-in categories

```bash
uv run --directory {baseDir} news fetch <category>
uv run --directory {baseDir} news fetch --all
uv run --directory {baseDir} news fetch <category> -l 20
```

Available categories: `top` · `world` · `gov` · `politics` · `us` · `middle-east` · `russia-ukraine` · `indonesia` · `japan` · `korea` · `ai`

For time-window queries, sync to SQLite first:

```bash
uv run --directory {baseDir} news sync <category>
uv run --directory {baseDir} news query <category> --since 24h
uv run --directory {baseDir} news query <category> --since '2026-03-09T00:00:00+08:00' --until '2026-03-10T00:00:00+08:00'
```

Prefer ISO 8601 with timezone for `--since` / `--until`. See `references/cli.md` for the full command reference.

Use `scripts/data/sources.json` as the runtime source of truth for feed URLs and category coverage.

For any region- or topic-specific request, always scan the `top` feed in parallel and include relevant top-headline items that would otherwise be missed.

### Direct RSS URL

```bash
uv run --directory {baseDir} news rss <RSS_URL>
uv run --directory {baseDir} news rss <RSS_URL> -l 20
```

Infer source, region, and topic from the feed URL or metadata. Do not ask follow-up questions unless the feed is unreadable or clearly ambiguous.

## Process and format

After fetching, follow this workflow:

1. **Scope** — Confirm topic, region, and time window. Default to the last 48 hours if unspecified.
2. **Filter** — Use `--since` / `--until` to narrow the time window at the script level. Manually remove off-topic or low-value items that slip through.
3. **Deduplicate and merge** — Combine multi-source reports of the same event into a single entry, preserving all valid sources.
4. **Section and rank** — Group by topic/conflict/policy thread, then rank by impact within each group.
5. **Rewrite** — Distill each item into a headline + 2-sentence summary in the user's language. Preserve timestamps and source links.
6. **Wrap up** — Add a "核心观察" paragraph summarizing the key shift, core tension, and what to watch next.

Read `references/filtering-formatting.md` in full before drafting. It is the execution standard for filtering criteria, deduplication rules, section layout, writing style, and formatting. Do not improvise these rules from memory.

## References

| File | Purpose |
|---|---|
| `scripts/data/sources.json` | Runtime source of truth for categories and feed URLs |
| `references/sources.md` | Built-in RSS feed list and historical reference |
| `references/cli.md` | Full CLI usage for fetch, sync, and query |
| `references/filtering-formatting.md` | Filtering, deduplication, sectioning, writing style, and layout rules |
