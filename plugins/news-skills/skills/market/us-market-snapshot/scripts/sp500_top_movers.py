#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "lxml>=6.0.2",
#     "pandas>=3.0.1",
#     "yfinance>=1.2.0",
# ]
# ///

import io
import sys
import urllib.request
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf


SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def get_sp500_constituents() -> dict[str, str]:
    try:
        req = urllib.request.Request(SP500_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            html_content = response.read()
        sp500_table = pd.read_html(io.BytesIO(html_content))[0]
    except Exception as exc:
        print(f"Error: failed to fetch S&P 500 constituents: {exc}", file=sys.stderr)
        raise SystemExit(1)

    constituents = {}
    for _, row in sp500_table.iterrows():
        symbol = row["Symbol"].replace(".", "-")
        constituents[symbol] = row["Security"]
    return constituents


def is_missing(value) -> bool:
    return value is None or pd.isna(value)


def format_price(value):
    if is_missing(value):
        return "n/a"
    return f"${float(value):,.2f}"


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


def truncate(value, width):
    text = str(value)
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def latest_two(series):
    values = series.dropna()
    if len(values) < 2:
        return None
    return values.index[-1], values.iloc[-1], values.index[-2], values.iloc[-2]


def print_rule(width=96):
    print("─" * width)


def main():
    constituents = get_sp500_constituents()
    tickers = list(constituents)

    try:
        data = yf.download(
            tickers=tickers,
            period="5d",
            interval="1d",
            group_by="ticker",
            progress=False,
            auto_adjust=False,
        )
    except Exception as exc:
        print(f"Error: failed to download S&P 500 prices: {exc}", file=sys.stderr)
        raise SystemExit(1)

    if data.empty:
        print("Error: no S&P 500 price data returned from Yahoo Finance", file=sys.stderr)
        raise SystemExit(1)

    rows = []
    warnings = []

    for ticker in tickers:
        try:
            if ticker not in data.columns.get_level_values(0):
                warnings.append(f"{ticker}: no downloaded price table")
                continue

            ticker_data = data[ticker]
            close_pair = latest_two(ticker_data["Close"])
            if close_pair is None:
                warnings.append(f"{ticker}: fewer than two valid close prices")
                continue

            latest_date, latest_close, previous_date, previous_close = close_pair
            if previous_close == 0:
                warnings.append(f"{ticker}: previous close is zero")
                continue

            volume_series = ticker_data["Volume"]
            latest_volume = volume_series.get(latest_date)
            previous_volume = volume_series.get(previous_date)
            volume_change_pct = (
                (latest_volume - previous_volume) / previous_volume * 100
                if not is_missing(previous_volume) and previous_volume > 0
                else None
            )

            rows.append(
                {
                    "symbol": ticker,
                    "name": constituents[ticker],
                    "date": latest_date,
                    "close": latest_close,
                    "change_pct": (latest_close - previous_close) / previous_close * 100,
                    "volume": latest_volume,
                    "volume_change_pct": volume_change_pct,
                }
            )
        except Exception as exc:
            warnings.append(f"{ticker}: {exc}")

    if not rows:
        print("Error: no valid S&P 500 mover rows could be calculated", file=sys.stderr)
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        raise SystemExit(1)

    df = pd.DataFrame(rows)
    top_gainers = df.nlargest(10, "change_pct")
    top_losers = df.nsmallest(10, "change_pct")
    latest_date = max(row["date"] for row in rows)

    print_rule()
    print("S&P 500 Top Movers")
    print_rule()
    print(f"As of: {format_date(latest_date)}")
    print("Source: S&P 500 constituents from Wikipedia; prices from Yahoo Finance via yfinance")
    print("Change: latest close vs previous valid close")
    print(f"Universe: {len(tickers)} constituents; Calculated: {len(rows)}; Skipped: {len(warnings)}")
    print_rule()

    def print_table(title, frame):
        print(f"\n[{title}]")
        print(f"{'Rank':<4} {'Symbol':<7} {'Name':<30} {'Close':>12} {'Change':>10} {'Volume':>12} {'Vol Chg':>10}")
        print("─" * 96)
        for rank, (_, row) in enumerate(frame.iterrows(), 1):
            print(
                f"{rank:<4} "
                f"{row['symbol']:<7} "
                f"{truncate(row['name'], 30):<30} "
                f"{format_price(row['close']):>12} "
                f"{format_percent(row['change_pct']):>10} "
                f"{format_volume(row['volume']):>12} "
                f"{format_percent(row['volume_change_pct']):>10}"
            )

    print_table("Top 10 Gainers", top_gainers)
    print_table("Top 10 Losers", top_losers)
    print_rule()

    if warnings:
        print(f"Warnings: {len(warnings)} symbol(s) skipped or partially unavailable", file=sys.stderr)
        for warning in warnings:
            print(f"- {warning}", file=sys.stderr)


if __name__ == "__main__":
    main()
