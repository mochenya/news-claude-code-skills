---
name: scheduled-news-briefs
description: >-
  Use when creating, reviewing, migrating, or modifying recurring news-brief
  automation: system-crontab launcher scripts, collector scripts, hermes send
  IM delivery (Telegram topics), or multiple non-overlapping intraday windows.
  Covers message-first prompts, time-window design, market-data supplements,
  legacy cleanup, and end-to-end verification. Trigger on 定时简报、
  增量新闻任务、早中晚三次推送、修改crontab、新闻脚本调度、Telegram话题投递.
  Not for generating a one-off brief or scheduling a simple reminder.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [news, cron, scheduling, briefing, telegram, automation]
    related_skills: [jp-kr-news-brief, rss-fetcher, news-briefing]
---

# Scheduled News Briefs

## Overview

Design recurring news briefs as a small pipeline with clear ownership:

1. **Launcher script** `cron/run-{job-slug}.sh` owns environment, lock, logging, the prompt and the schedule (installed in the system crontab).
2. **Collector script** computes an exact time window and emits candidate data.
3. **Topic skill** defines filtering and formatting.
4. **Agent task** (`hermes chat -q`) produces the brief and performs delivery itself with `hermes send --to`.

Keep news selection and prose inside the agent task. Keep deterministic time calculation and RSS collection inside the script. Delivery is an explicit, mandatory step inside the prompt — not an implicit framework side effect.

Any scheduled task that pushes to an IM channel (Telegram, Feishu, …) MUST use this launcher + system crontab route. Do not create Hermes built-in cron jobs for IM delivery: their `deliver` target fails silently when misconfigured, and removing a job leaves the crontab `cron tick` wake-up spinning with exit 0. Author launchers with the `cron-script-generator` skill.

## When to Use

- A brief runs daily or several times per day.
- The user wants contiguous incremental windows with no overlap.
- A scheduled job needs RSS candidates plus live market-data supplementation.
- A Hermes built-in cron job must be migrated onto a system-crontab launcher.
- Delivery must move to a specific Telegram chat/topic.

Do not use for a one-shot news request or a generic “remind me” task.

## Architecture

### Collector script

The script should be deterministic and produce context, not prose. Its stdout should contain:

```text
report_slot=<slot>
report_mode=<mode>
window_start=<ISO-8601 +08:00>
window_end=<ISO-8601 +08:00>
rss_candidates_json_begin
[...]
rss_candidates_json_end
```

Use `[window_start, window_end)` throughout. Exit non-zero when collection fails so the launcher cannot mistake a broken collector for an empty window.

The collector is invoked from inside the launcher (or from the prompt's deterministic step) and only produces structured data. It never sends messages.

### Launcher script

Build the launcher with the `cron-script-generator` skill. Its `HERMES_QUERY` must additionally carry the launcher-specific contract: which topic skill / output-format reference to load, the fixed delivery target with the exact `hermes send --to` command to run, and completion conditions that require a verified send receipt.

### Prompt

Every scheduled news prompt must be self-contained and state:

- the report type and exact window semantics;
- **以消息为主** / news is primary;
- incremental deduplication rules;
- which output-format reference to load;
- whether market data is required for this slot;
- zero-result behavior;
- “only output the brief body.”

### Delivery

Delivery is explicit: the agent writes the final brief to a task-specific temp file, verifies it is non-empty, then runs `hermes send --to "<target>" --file <path> --json` and treats a non-zero exit as task failure. Never rely on the agent's final response being auto-delivered.

For Telegram forum topics, a topic-root link of the form:

```text
https://t.me/c/<internal_chat>/<topic_root_message>
```

usually maps to:

```text
telegram:-100<internal_chat>:<topic_root_message>
```

If the link points to an ordinary message rather than the topic root, verify the actual thread ID before updating jobs.

## Workflow

### 1. Inspect before changing

List Hermes jobs and read the live system crontab. Search for legacy launchers, stale job IDs, generator mappings, and duplicate schedules. Do not rely on memory alone.

Completion criterion: every existing execution path for the target brief is accounted for.

### 2. Define contiguous windows

Use half-open windows so adjacent runs neither overlap nor leave gaps:

```text
slot A: [T0, T1)
slot B: [T1, T2)
slot C: [T2, T3)
```

Prompts should state that repeated coverage is allowed only when an event has a substantive new development.

### 3. Build and exercise collectors

Create one script per slot or one deterministic parameterized collector. Verify:

- shell/Python syntax;
- computed Beijing-time bounds;
- valid JSON or structured stdout;
- every returned item lies inside the stated window;
- no production `--limit` truncates candidates before filtering.

### 4. Create or update the launcher

Create `cron/run-{job-slug}.sh` following `cron-script-generator`: env header, `flock -n`, log path, `DRY_RUN=1` support, `HERMES_QUERY` with the topic skill and the fixed `hermes send --to` target. Verify with `sh -n`, `chmod +x`, and a dry run.

### 5. Install into system crontab

Add exactly one line per launcher at the requested time. Stagger new briefs against existing schedules to avoid collisions (check `crontab -l` first).

Install safely: export `crontab -l` to a temp file, append the new line there, diff the temp file against the live crontab, then `crontab /tmp/<file>`. Never pipe through `sed` directly into `crontab -`. Re-read `crontab -l` afterwards and confirm no duplicates.

### 6. Remove superseded paths

When migrating a job off Hermes built-in cron (or replacing an old brief):

- remove the Hermes job (`cronjob action='remove'`) and any leftover `cron tick` crontab line for that profile;
- delete stale lock files and obsolete `/tmp` report copies;
- remove generator mappings that could recreate the superseded launcher;
- keep only the new launcher, collector scripts, and active crontab lines.

Completion criterion: searching active cron assets and `cronjob list` finds no reference to the superseded launcher or job ID.

### 7. Verify end to end

Minimum verification:

- collector scripts return valid in-window data;
- launcher passes `sh -n`, is executable, and `DRY_RUN=1` prints the command without running it;
- system crontab contains the intended launcher line and no legacy or duplicate line;
- `cronjob list` shows no surviving Hermes job for the same brief;
- the log file of the latest real run shows a successful `hermes send` receipt;
- invisible-Unicode scan passes for attached skills/prompts.

Run one job manually only when an immediate test delivery is useful and will not create unwanted channel noise.

## Message-First Market Briefs

Market information is secondary to news unless the user asks for a dedicated market report.

- **Morning/overnight:** prioritize new policy, macro, trade, industry, and geopolitical messages.
- **Midday:** retain news as the body; add a compact as-of market snapshot.
- **Evening/post-close:** retain latest news as the body; add closing data and a short next-session watchlist.

Facts and interpretation must be separated. Intraday values need an “as of” timestamp. On holidays, state the closure and never relabel the previous close as today's data.

See `references/intraday-window-patterns.md` for the Japan/Korea three-slot pattern and market-session nuance.

## Common Pitfalls

1. **Hermes built-in cron job for an IM-pushing brief** — silent delivery failure and stale `cron tick` spinners; use a launcher + system crontab instead.
2. **Relying on final-response auto-delivery** — the agent must run `hermes send --to` and confirm the receipt.
3. **`sed | crontab -`** — a failing intermediate command empties the whole crontab; always temp file → diff → `crontab <file>`.
4. **Direct collector execution without an agent step** — data is produced but no brief or delivery runs.
5. **Delivery target written vaguely** — always the full `platform:chat:thread` triple in the launcher.
6. **Overlapping windows** — produces repeated headlines and ambiguous “incremental” claims.
7. **Calling every midday number a close** — some markets trade continuously; label those as intraday snapshots.
8. **Removing a launcher but leaving its generator mapping or Hermes job** — the obsolete path can reappear later.

## Verification Checklist

- [ ] All existing execution paths inspected
- [ ] Windows are contiguous half-open intervals
- [ ] Collector scripts exercised with valid structured output
- [ ] Prompts explicitly say news is primary
- [ ] Launcher verified: `sh -n`, executable, DRY_RUN, fixed `hermes send --to` target
- [ ] System crontab re-read after install: intended lines only, no duplicates
- [ ] No surviving Hermes cron job or `cron tick` line for the same brief
- [ ] Legacy lock files and generator mappings removed
- [ ] Market-session labels and holiday behavior are accurate
- [ ] Latest real run's log shows a successful send receipt
