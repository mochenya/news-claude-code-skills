---
name: rss-brief-skill-design
description: >-
  Use when creating, reviewing, renaming, or restructuring a region- or
  topic-specific RSS news-brief Skill. Covers trigger boundaries, canonical
  --since/--until CLI design, progressive disclosure between SKILL.md and
  references/, single-source-of-truth output formatting, and verification.
  Trigger on requests such as 优化RSS Skill、重构新闻源 Skill、设计地区新闻简报
  Skill、把排版拆到 reference、修改新闻 Skill description. Not for generating
  a news brief itself or maintaining one feed URL.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, rss, news, briefing, architecture, authoring]
    related_skills: [rss-fetcher, news-briefing, hermes-agent-skill-authoring]
---

# RSS Brief Skill Design

## Overview

Design class-level Skills for recurring regional or topical RSS briefs. The goal is a short, reliable main `SKILL.md` that exposes the high-frequency execution path while detailed formatting, filtering edge cases, and source maintenance live under `references/`.

The main file is an execution surface, not a source catalog, operational diary, or full CLI manual.

## When to Use

Use this Skill when:

- creating a reusable RSS brief Skill for a region or topic;
- reviewing whether an existing news Skill has grown too broad or too verbose;
- separating output formatting from source-specific notes;
- tightening frontmatter triggers and counter-triggers;
- adding or correcting strict time-window behavior;
- renaming a Skill so its name reflects the recurring task rather than its implementation.

Do not use it to generate today’s brief, research one feed, or document a transient environment failure.

## Target Architecture

```text
<region-or-topic>-news-brief/
├── SKILL.md
├── references/
│   ├── output-format.md       # mandatory every time a brief is drafted
│   ├── filtering-notes.md     # load only for ambiguous/duplicate candidates
│   └── source-maintenance.md  # load only for feed coverage or failures
├── scripts/                   # deterministic fetch/filter implementation
└── tests/                     # time-window and CLI behavior tests
```

Names should describe the recurring user outcome, such as `jp-kr-news-brief`, rather than an internal library, feed vendor, date, cron job, or one-off incident.

## Main SKILL.md: Keep the Hot Path Hot

The main file should contain only information needed on most runs:

1. **Trigger boundary** — broad requests for recent regional/topic news load the Skill; narrow single-fact searches and general web search do not.
2. **Goal and scope** — one short paragraph explaining what brief is produced.
3. **Canonical time-window command** — one production command, not a menu of rarely used subcommands.
4. **Core processing sequence** — hard time filter, relevance filter, semantic deduplication, selective enrichment, importance ranking.
5. **Mandatory formatting pointer** — explicitly load the one authoritative output-format reference before drafting.
6. **Completion checklist** — checkable requirements, including window fidelity and source links.

A data-source sentence is enough in the main file: the configured source set is managed internally and normally does not require user or agent selection.

### Progressive-disclosure rule

Before adding a paragraph, ask:

- Is this needed on every execution? Put it in `SKILL.md`.
- Is it needed only for a branch, edge case, or maintenance task? Put it in `references/`.
- Is it a deterministic operation or validator? Put it in `scripts/`.
- Is it a reusable starter artifact? Put it in `templates/`.

## Frontmatter Trigger Design

The description must encode both positive triggers and boundaries.

Good shape:

```yaml
description: >-
  Use when the user asks for recent <region/topic> news or a time-windowed
  <region/topic> brief, including midday, overnight, and post-close reports,
  even if RSS is not mentioned. Uses mandatory Beijing-time --since/--until
  filtering and the output contract in references/output-format.md. Do not
  load for general web search, non-scope topics, a single fact/article search,
  or standalone live-quote requests.
```

Rules:

- Trigger on the user’s task language, not only implementation words like “RSS”.
- State the non-trigger boundary directly.
- Avoid listing every feed in the description; source names are not the user outcome.
- Keep the description focused enough that unrelated web searches do not load the Skill.

## Canonical Time-Window CLI Contract

A production brief should expose one standard command:

```bash
uv run --directory "$SKILL_DIR" <cli> fetch --all \
  --since "$START" \
  --until "$END" \
  -f json
```

Required semantics:

- `--since` and `--until` are both required.
- Timestamps are timezone-aware ISO 8601; use the reporting timezone explicitly.
- The interval is half-open: `[START, END)`.
- Default execution scans all currently visible feed entries before filtering.
- Do not apply a small per-source limit before time filtering; that silently drops older in-window items.
- JSON output preserves source, title, link, description, and normalized publication time.
- Undated or unparsable entries are excluded from strict-window output.

If the underlying CLI does not enforce these semantics, add tests first, observe them fail, then implement the smallest behavior change that makes them pass.

## Output Formatting: One Source of Truth

Put the complete layout contract in `references/output-format.md`. It should define:

- standard brief vs midday/market-hours/post-close variants;
- Chinese headline and summary rules;
- Beijing-time and Markdown-source metadata lines;
- dynamic sectioning and importance ranking;
- market data timing and attribution discipline;
- investment-observation or closing section requirements;
- zero-item output;
- final verification checklist.

The main `SKILL.md` should only say that this reference is mandatory before drafting and summarize which modes it contains.

Do not copy the full template back into the main file. Two copies drift, and future agents cannot know which one is authoritative.

## Filtering and Source References

Use `references/filtering-notes.md` for conditional reasoning:

- regional/topic inclusion and exclusion priorities;
- semantic deduplication patterns;
- title-only article enrichment;
- cross-source conflict handling;
- when supplementary web extraction/search is justified.

Use `references/source-maintenance.md` only for maintenance:

- runtime source-of-truth location;
- source inventory and coverage roles;
- retired feeds and reasons;
- paywalls, missing summaries, and source overlap;
- feed health checks.

Do not let source history dominate the main execution path. Users normally care about the time window and final brief, not which feed supplied each candidate before filtering.

## Market-Brief Branch

A region-specific news Skill may support midday or post-close reports without becoming a live-quote Skill.

- RSS remains the news-candidate source.
- Current index, FX, rate, and sector data may be supplemented from verifiable market sources.
- Intraday data must be labeled “as of HH:mm”; never call it a closing value.
- Causal reporting and analyst inference must be distinguished.
- A standalone quote request should route to a market-data/search Skill instead.

Keep these detailed layout rules in `output-format.md`; the main Skill needs only the mode-selection rule.

## Workflow

1. **Survey** — Read the existing main file and all linked references. Identify duplicated content and stale pointers.
2. **Define the class** — Confirm the Skill represents a recurring region/topic brief, not one run or one feed.
3. **Name** — Prefer `<scope>-news-brief`; update directory, frontmatter, references, and consumers together.
4. **Tighten triggers** — Add positive task-language triggers and explicit general-search/single-fact boundaries.
5. **Choose the hot path** — Keep one canonical strict-window command in the main file.
6. **Split detail** — Move formatting, filtering edge cases, and source maintenance into separate references.
7. **Align implementation** — Ensure the CLI behavior matches the documented window semantics.
8. **Verify** — Test required arguments, boundary inclusion/exclusion, full-feed scanning, real output, frontmatter, linked files, and invisible Unicode.

Completion criterion: a new session can load the Skill, run the common time-window command, read one mandatory formatting reference, and produce the expected brief without reading source-maintenance history.

## Common Pitfalls

1. **Source catalog as main content** — it makes the Skill look like feed documentation rather than an execution workflow.
2. **Many CLI examples** — agents choose inconsistent paths. Keep one production command; move full CLI help elsewhere.
3. **Optional window flags with “strict window” prose** — documentation and behavior disagree.
4. **Limit before filter** — a per-source cap can silently omit valid in-window items.
5. **Formatting duplicated in two files** — rules drift. Keep one authoritative reference.
6. **Cron/delivery instructions inside the RSS Skill** — scheduling belongs to the scheduler/job configuration, not the reusable news-processing Skill.
7. **Source names as triggers** — this overfits routing to implementation and misses natural user requests.
8. **Transient failures as permanent rules** — preserve the durable fix or verification pattern, not a temporary environment state.

## Verification Checklist

- [ ] Skill name describes a recurring brief class, not a session artifact
- [ ] Description contains positive triggers and explicit counter-triggers
- [ ] Main file focuses on time-window execution and the formatting entrypoint
- [ ] Exactly one canonical production CLI path is prominent
- [ ] `--since/--until` semantics match implementation and tests
- [ ] No small default limit truncates candidates before filtering
- [ ] Full output template exists only in `references/output-format.md`
- [ ] Filtering and source details are conditionally loaded references
- [ ] All referenced files exist and are linked from the main file
- [ ] Frontmatter validates and invisible Unicode scan is clean
- [ ] Renamed Skills have no stale consumer references

## References

- `references/reference-layout.md` — canonical file split, frontmatter pattern, and migration checklist for specialized RSS brief Skills.
