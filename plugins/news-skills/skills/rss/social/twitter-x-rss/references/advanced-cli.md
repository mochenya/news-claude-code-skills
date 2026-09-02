# xfactions CLI reference for X monitoring

The legacy RSS CLI has been retired. Use the installed CLI and explicit database path:

```bash
XF=/home/lht/.local/bin/xfactions
DB=/home/lht/.config/xfactions/xfactions.db
```

## Sync and query contract

```bash
$XF --db "$DB" sync --faction <faction>
$XF --db "$DB" sync status
$XF --db "$DB" query posts --faction <faction> \
  --from <UTC_RFC3339> --to <UTC_RFC3339> --output ndjson
```

`sync` may access the provider and write SQLite. `query posts` is local-only. Query intervals are UTC and half-open: `[from, to)`.

For every command, check process exit code and the JSON envelope. A sync exit code of `2` means partial or total remote failure even if the JSON envelope itself is well-formed. Inspect `data.failed` and `data.users[].error`.

NDJSON emits one post per line and ends with a summary envelope. The final envelope is not a post.

See the `xfactions-cli` skill for the full current command and field contract.