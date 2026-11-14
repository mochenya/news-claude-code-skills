# Cron Fleet Consistency Audit

For requests like "check all our scheduled news prompts/workflows for inconsistencies", audit mechanically — do not read N launchers and eyeball them.

## Method

1. **Scope from live state, not memory**: `crontab -l` plus `ls cron/run-*.sh`. Commented crontab lines are disabled jobs — audit only enabled ones, list disabled separately.
2. **Dump all launchers to one JSON map** in the workspace (cat each script into a dict), then compare with Python regexes across the whole fleet in one pass. Never head-to-head compare file-by-file.
3. **Invariant checks to run over the dump**:
   - `HERMES_QUERY="$(cat <<'EOF'` — heredoc must be QUOTED. An unquoted `<<EOF` lets the shell expand backticks and `$...` inside the prompt text (latent corruption bug even when current text is benign).
   - Variables defined but never referenced (e.g. `DELIVER=`, `JOB_NAME=` with zero `$VAR` uses) — hermes-cronjob-era dead code from migrations.
   - `hermes send` command form inside each prompt: `--to/--file` vs `-t/-f` vs stdin heredoc pipe vs `MEDIA:` attachment. Functionally equivalent, contractually divergent.
   - Delivery-receipt acceptance wording ("success / sent" vs `"success": true` + `message_id` vs `"sent"`) and retry policy (retry-once / explicit no-retry-loop / outer script sends after validation). These must be identical across jobs or explicitly justified.
   - Which skills each prompt loads — every news brief must load the shared bottom-line layer (`investor-news-guidance`); a prompt that skips it is drift.
   - Time-window lines per job (start/end anchors vs cron fire time) — tabulate; same "overnight" label with different anchors (20:00 vs 22:00 start, 07:30 vs 08:00 end) is a finding.
   - All `telegram:chat:thread` targets: which topics are shared by multiple jobs.
4. **Resolve referenced absolute paths**: grep the fleet + its named skills for referenced data files/dirs (shared profile dirs, `references/*.md`, state files) and check each exists on this host. A restored/migrated crontab carries prompts that reference files which only exist on the old machine — scripts run "successfully" while their mandated pre-reads silently no-op.
5. **Shared mutable state**: detect two jobs writing or reading the same file (latest-brief markdown, heartbeat state) or delivering to the same topic — later runs clobber earlier content and streams interleave. Confirm with the user whether intended.
6. **Report tiered**: 🔴 substantive breakage (missing referenced data, shared-file races) → 🟡 contract drift (receipt wording, send form, retry policy, window anchors) → ⚪ dead code. Ask which tiers to fix; do not bulk-edit launchers without approval (user expects minimal-scope changes).

## Standardization targets when fixing

- One quoted-heredoc template, one send form (`hermes send --to <target> --file <path> --json`), one receipt contract (`success`/`sent` + message id), one retry rule (retry once, then non-zero exit).
- New six-section prompt shape (任务名称 / 执行前 / 时间窗口 / 专题使命 / 最后一步 / 完成条件) over legacy "第一步～第四步" bodies that embed collection commands and /tmp paths.
- Remove unused `DELIVER`/`JOB_NAME` when touching a launcher; note leftover dead vars elsewhere in the audit report rather than drive-by refactoring untouched jobs.
