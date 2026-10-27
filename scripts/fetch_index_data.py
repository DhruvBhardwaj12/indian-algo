"""Fetch Nifty 50 and Bank Nifty index data for pairs trading.

Run:
    uv run python scripts/fetch_index_data.py
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from indian_algo.data.nse_fetcher import fetch_symbol, save_parquet

TICKERS = {
    "^NSEI": "NIFTY50",
    "^NSEBANK": "BANKNIFTY",
}

INTERVALS = ["15m", "1d"]
OUT_DIR = Path("data/raw/nse/indices")


def main() -> None:
    for ticker, name in TICKERS.items():
        for interval in INTERVALS:
            period = "60d" if interval == "15m" else "2y"
            try:
                df = fetch_symbol(ticker, interval=interval, period=period)
                if df.empty:
                    continue
                # Rename symbol for clean file paths
                df["symbol"] = name
                out = OUT_DIR / name / interval / f"{period}.parquet"
                save_parquet(df, out)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed {} {}: {}", ticker, interval, exc)

    logger.success("Index data fetched.")


if __name__ == "__main__":
    main()
    