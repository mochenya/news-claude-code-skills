# Faction membership migration

`config/factions.json` is a historical, one-time import source for the retired RSS monitor. It is not a live configuration file.

Runtime membership authority is the `xfactions` database:

```bash
XF=/home/lht/.local/bin/xfactions
DB=/home/lht/.config/xfactions/xfactions.db
$XF --db "$DB" watch list
```

Use `watch add` and `watch remove` to manage current memberships. A handle may have multiple faction/group memberships; a membership change preserves historical posts.

Do not re-import or edit the historical JSON during normal scheduled runs.