# Official Sources

## Primary

| Market | Primary | Fallback search |
|--------|---------|-----------------|
| A-shares | https://www.sse.com.cn/disclosure/dealinstruc/closed/ | `site:sse.com.cn 休市安排 {year}` · `site:szse.cn 休市安排 {year}` |
| HKEX | Annual PDF: Hong Kong Securities Market Holiday Schedule for Year {year} | `Hong Kong Securities Market Holiday Schedule for Year {year} site:hkex.com.hk` |
| US | https://www.nyse.com/markets/hours-calendars | `NYSE holidays early closings {year} site:nyse.com` |

Notes:
- A-shares: SSE/SZSE/BSE equity days usually match; ChinaClear only if settlement asked.
- HKEX: full holiday ≠ half-day / non-settlement.
- US: early close often 1:00 p.m. ET; flag observed holidays.

## Other markets

Search: `{keywords} {year} site:{domain}` → open operator page/PDF only.

| Market | Domain | Keywords |
|--------|--------|----------|
| Japan (JPX/TSE) | jpx.co.jp | trading calendar, holidays, 休場日 |
| Korea (KRX) | krx.co.kr | market holiday, trading calendar, 휴장 |
| Singapore (SGX) | sgx.com | trading calendar, market holidays |
| Taiwan (TWSE) | twse.com.tw | trading calendar, 假期, 休市 |
| UK (LSE) | londonstockexchange.com | trading calendar, market holidays |
| Euronext | euronext.com | trading calendar, holidays |
| Germany (Xetra) | deutsche-boerse.com, xetra.com | trading calendar, holidays |
| Australia (ASX) | asx.com.au | trading calendar, market holidays |
| Canada (TSX) | tsx.com | trading calendar, market holidays |
| India (NSE/BSE) | nseindia.com, bseindia.com | trading holidays, market holidays |

Generic: `{exchange} holiday schedule {year} site:{domain}`

## Authority

1. Official URL / annual PDF  
2. `site:` on exchange domain  
3. Fail openly if only media hits  

Not sole authority: `exchange_calendars`, `pandas_market_calendars`, akshare/tushare, news rewrites.
