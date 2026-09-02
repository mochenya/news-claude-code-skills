---
name: us-market-snapshot
description: Run local scripts for a US market snapshot. Use when the user asks about S&P 500, Dow Jones, Nasdaq Composite, Nasdaq 100, KWEB, PGJ, WTI crude oil, Brent crude oil, broad US market performance, China internet ETFs, crude oil prices, or S&P 500 top gainers/losers. Always run the script instead of answering from memory.
---

# US Market Snapshot

Run the local scripts and answer from their terminal output.

## Market snapshot

Use for S&P 500, Dow Jones, Nasdaq Composite, Nasdaq 100, KWEB, PGJ, WTI crude oil, Brent crude oil, or broad US market performance.

```bash
uv run {baseDir}/scripts/index_tracker.py
```

Output includes:
- `As of`: latest trading date in ET
- `Source`: data source
- `Change`: latest close vs previous valid close
- `Close`, `Volume`, `Vol Chg`: latest values from the script

## S&P 500 top movers

Use for top gainers, top losers, biggest movers, strongest stocks, or weakest stocks in the S&P 500.

```bash
uv run {baseDir}/scripts/sp500_top_movers.py
```

Output includes:
- `As of`: latest trading date in ET
- `Source`: data source
- `Universe`, `Calculated`, `Skipped`: coverage summary
- top 10 gainers and top 10 losers

## Rules

- Always run the relevant script before answering.
- Do not use memory or estimate current market data.
- Include the `As of` date in the answer.
- Keep the script's change basis: latest close vs previous valid close.
- Mention warnings or skipped data if shown.
- If the script fails, report the failure instead of inventing data.
- Keep the final answer concise.
