---
name: market-calendar
description: "Check if a date is an exchange trading day; list holiday closures and early closes/half-days. Use for A-shares (SSE/SZSE/BSE), HKEX, NYSE/Nasdaq, or other markets (JPX, KRX, SGX, etc.) when users ask trading day, closed days, holiday schedule, early close, half-day, or observed holiday. Never answer from memory—use official exchange pages."
---

# Market Calendar

## Workflow

1. Parse market(s) + date/range + whether early close/half-day is needed.
2. Open the fixed official URL (below). No finance blogs first.
3. Extract only the requested range: full close | early close/half-day | “weekends closed as usual” (do not list every weekend unless a day-by-day calendar is asked).
4. If the page is missing/stale → site-scoped search in [`references/official-sources.md`](references/official-sources.md).
5. Prefer **one open per market**. Single-day → yes/no + one-line reason + source.

## Market paths

### A-shares (SSE / SZSE / BSE)

1. Open `https://www.sse.com.cn/disclosure/dealinstruc/closed/`
2. Equity days are usually aligned across the three; one page is enough unless settlement differs.
3. Fallback: `site:sse.com.cn 休市安排 {year}`

### HKEX

1. Search `Hong Kong Securities Market Holiday Schedule for Year {year} site:hkex.com.hk`
2. Open the year’s circular PDF.
3. Split full holiday vs half-day / non-settlement.

### US (NYSE / Nasdaq)

1. Open `https://www.nyse.com/markets/hours-calendars`
2. Holidays vs Early Closings; flag observed holidays.
3. NYSE covers cash equities unless Nasdaq differences are asked.
4. Fallback: `NYSE holidays early closings {year} site:nyse.com`

### Other markets

`{holiday keywords} {year} site:{operator domain}` → open official HTML/PDF only. Domains/keywords: [`references/official-sources.md`](references/official-sources.md).

## Output

Single day:
```text
{Market}: trading day | closed | early close/half-day — {reason}
Source: {exchange}
```

Range:
```text
{Market}
- YYYY-MM-DD: full close — {reason}
- YYYY-MM-DD: early close/half-day — {time if known}
- Weekends closed as usual
Source: {exchange}
```

## Rules

- Do not invent holidays.
- Early close/half-day ≠ full close.
- Secondary sites/calendar libs are not sole authority.
- Do not expand to full year unless asked.
