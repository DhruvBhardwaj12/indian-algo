"""Fetch NSE historical data for the scalp universe.

Run:
    uv run python scripts/fetch_nse_data.py
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from indian_algo.data.nse_fetcher import fetch_symbol, save_parquet

SYMBOLS = [
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "INFY.NS",
    "TATAMOTORS.NS",
    "BAJFINANCE.NS",
    "BHARTIARTL.NS",
    "ADANIENT.NS",
    "SBIN.NS",
    "VEDL.NS",
]

INTERVALS = ["5m", "15m", "1h", "1d"]

OUT_DIR = Path("data/raw/nse")


def main() -> None:
    for symbol in SYMBOLS:
        for interval in INTERVALS:
            period = "60d" if interval in ("5m", "15m", "1h") else "2y"

            try:
                df = fetch_symbol(symbol, interval=interval, period=period)
                if df.empty:
                    continue
                out = OUT_DIR / symbol.replace(".", "_") / interval / f"{period}.parquet"
                save_parquet(df, out)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed {} {}: {}", symbol, interval, exc)

    logger.success("All symbols fetched.")


if __name__ == "__main__":
    main()
    