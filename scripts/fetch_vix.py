"""Fetch India VIX historical data."""

from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf
from loguru import logger

OUT_DIR = Path("data/raw/nse/indices/INDIAVIX/1d")

def main() -> None:
    logger.info("Fetching India VIX...")
    ticker = yf.Ticker("^INDIAVIX")
    df = ticker.history(period="2y", interval="1d")
    
    if df.empty:
        logger.error("Empty response for India VIX.")
        return
    
    df = df.reset_index().rename(columns={
        "Date": "timestamp", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume"
    })
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "2y.parquet"
    df.to_parquet(out, index=False)
    logger.success(f"Saved {len(df)} rows to {out}")

if __name__ == "__main__":
    main()
