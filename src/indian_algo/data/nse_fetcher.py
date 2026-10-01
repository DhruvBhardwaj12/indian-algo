"""NSE historical data fetcher via yfinance.

Fetches OHLCV for NSE-listed stocks. yfinance uses the '.NS' suffix
(e.g., 'RELIANCE.NS').

Yahoo limits intraday history to 60 days. Daily is unlimited.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf
from loguru import logger


def fetch_symbol(symbol: str, interval: str, period: str = "60d") -> pd.DataFrame:
    """Fetch OHLCV for a single NSE symbol."""
    logger.info("Fetching {} at {} ({})", symbol, interval, period)
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=False)

    if df.empty:
        logger.warning("Empty response for {} at {}", symbol, interval)
        return pd.DataFrame()

    df = df.reset_index()
    time_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={
        time_col: "timestamp",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if df["timestamp"].dt.tz is None:
        if interval == "1d":
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
        else:
            df["timestamp"] = df["timestamp"].dt.tz_localize("Asia/Kolkata").dt.tz_convert("UTC")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    df["symbol"] = symbol
    df["interval"] = interval
    df["source"] = "yahoo_finance"
    df["fetched_at"] = datetime.now(timezone.utc)

    logger.success("Fetched {} rows for {} at {}", len(df), symbol, interval)
    return df


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="snappy")
    logger.success("Saved {} rows to {}", len(df), path)
    