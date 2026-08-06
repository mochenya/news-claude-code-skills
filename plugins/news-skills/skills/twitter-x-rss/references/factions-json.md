# Factions JSON

Define each faction as a top-level name containing named account groups:

```json
{
  "musk": {
    "groups": {
      "core": ["elonmusk"],
      "companies": ["tesla", "spacex", "xai"]
    }
  }
}
```

- Pass the top-level name to `update-faction` or `query-faction`.
- Keep each account in only one group within a faction; the CLI rejects
  cross-group duplicates.
- Write account names with or without `@`; the CLI normalizes, lowercases, and
  deduplicates them.
- Group names organize human-readable query output and faction JSON output.
- Keep membership in this file. Synchronization state and collected posts live
  in SQLite.
