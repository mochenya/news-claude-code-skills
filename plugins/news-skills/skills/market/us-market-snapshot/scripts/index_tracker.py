#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "lxml>=6.0.2",
#     "pandas>=3.0.1",
#     "yfinance>=1.2.0",
# ]
# ///

import sys
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf


TICKERS = {
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones",
    "^IXIC": "Nasdaq Composite",
    "^NDX": "Nasdaq 100",
    "CL=F": "WTI Crude Oil",
    "BZ=F": "Brent Crude Oil",
    "KWEB": "China Internet - KWEB",
    "PGJ": "China Internet - PGJ",
}


def is_missing(value) -> bool:
    return value is None or pd.isna(value)


def format_number(value, decimal_places=2):
    if is_missing(value):
        return "n/a"
    return f"{float(value):,.{decimal_places}f}"


def format_volume(value):
    if is_missing(value):
        return "n/a"

    value = float(value)
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def format_percent(value):
    if is_missing(value):
        return "n/a"

    value = float(value)
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def format_date(index_value):
    et_timezone = ZoneInfo("America/New_York")
    if index_value.tzinfo is None:
        index_value = index_value.tz_localize(et_timezone)
    else:
        index_value = index_value.tz_convert(et_timezone)
    return index_value.strftime("%Y-%m-%d ET")


def latest_two(series):
    values = series.dropna()
    if len(values) < 2:
        return None
    return values.index[-1], values.iloc[-1], values.index[-2], values.iloc[-2]


def print_rule(width=78):
    print("─" * width)


def main():
    try:
        data = yf.download(
            tickers=" ".join(TICKERS),
            period="5d",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
    except Exception as exc:
        print(f"Error: failed to download market data: {exc}", file=sys.stderr)
        raise SystemExit(1)

    if data.empty:
        print("Error: no market data returned from Yahoo Finance", file=sys.stderr)
        raise SystemExit(1)

    rows = []
    warnings = []

    for ticker, name in TICKERS.items():
        try:
            close_pair = latest_two(data["Close"][ticker])
            if close_pair is None:
                warnings.append(f"{name}: fewer than two valid close prices")
                continue

            latest_date, latest_close, previous_date, previous_close = close_pair
            change_pct = (latest_close - previous_close) / previous_close * 100

            volume_series = data["Volume"][ticker]
            latest_volume = volume_series.get(latest_date)
            previous_volume = volume_series.get(previous_date)
            volume_change_pct = (
                (latest_volume - previous_volume) / previous_volume * 100
                if not is_missing(previous_volume) and previous_volume > 0
                else None
            )

            rows.append(
                {
                    "name": name,
                    "date": latest_date,
                    "close": latest_close,
                    "change_pct": change_pct,
                    "volume": latest_volume,
                    "volume_change_pct": volume_change_pct,
                }
            )
        except Exception as exc:
            warnings.append(f"{name}: {exc}")

    if not rows:
        print("Error: no valid market rows could be calculated", file=sys.stderr)
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        raise SystemExit(1)

    latest_date = max(row["date"] for row in rows)

    print_rule()
    print("US Market Snapshot")
    print_rule()
    print(f"As of: {format_date(latest_date)}")
    print("Source: Yahoo Finance via yfinance")
    print("Change: latest close vs previous valid close")
    print_rule()
    print(f"{'Market':<24} {'Close':>12} {'Change':>10} {'Volume':>12} {'Vol Chg':>10}")
    print_rule()

    for row in rows:
        print(
            f"{row['name']:<24} "
            f"{format_number(row['close']):>12} "
            f"{format_percent(row['change_pct']):>10} "
            f"{format_volume(row['volume']):>12} "
            f"{format_percent(row['volume_change_pct']):>10}"
        )

    print_rule()
    if warnings:
        print(f"Warnings: {len(warnings)} row(s) skipped or partially unavailable", file=sys.stderr)
        for warning in warnings:
            print(f"- {warning}", file=sys.stderr)


if __name__ == "__main__":
    main()
