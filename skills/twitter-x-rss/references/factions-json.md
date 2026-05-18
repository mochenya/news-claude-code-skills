# Factions JSON

`config/factions.json` maps a faction name to account groups.

## Recommended shape

```json
{
  "musk": {
    "groups": {
      "core": ["elonmusk"],
      "companies": ["tesla", "spacex", "xai"]
    },
    "last_sync_ts": null
  }
}
```

## Fields

- Top-level key: faction name, used by `update-faction` and `query-faction`.
- `groups`: group name to account list.
- Account names can include `@`, but plain names are cleaner.
- `last_sync_ts`: Unix timestamp for the last faction update. Use `null` for a new faction.

## Simple legacy shape

This also works, but it has no named groups:

```json
{
  "musk": ["elonmusk", "tesla", "spacex"]
}
```

## Tips

- Keep faction names short and stable.
- Group names only affect display and JSON output.
- The CLI lowercases account names and removes leading `@`.
