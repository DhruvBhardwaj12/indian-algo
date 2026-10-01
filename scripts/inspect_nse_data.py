"""Inspect the fetched NSE data — check for gaps, verify session hours.

Run:
    uv run python scripts/inspect_nse_data.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path("data/raw/nse")


def inspect(path: Path) -> None:
    df = pd.read_parquet(path)
    symbol = df["symbol"].iloc[0]
    interval = df["interval"].iloc[0]

    print(f"\n=== {symbol} @ {interval} ===")
    print(f"  Rows:        {len(df)}")
    print(f"  Columns:     {list(df.columns)}")
    print(f"  Date range:  {df['timestamp'].min()} -> {df['timestamp'].max()}")
    print(f"  NaNs:        {int(df.isna().sum().sum())}")
    print(f"  Duplicates:  {int(df['timestamp'].duplicated().sum())}")
    print(f"  Monotonic:   {df['timestamp'].is_monotonic_increasing}")

    # OHLC sanity
    bad_high = (df["high"] < df[["open", "close", "low"]].max(axis=1)).sum()
    bad_low = (df["low"] > df[["open", "close", "high"]].min(axis=1)).sum()
    print(f"  OHLC viols:  {int(bad_high + bad_low)}")

    # Session hour distribution (UTC): NSE session is 03:45-10:00 UTC
    df_local = df.copy()
    df_local["hour_utc"] = df_local["timestamp"].dt.hour
    hours = df_local["hour_utc"].value_counts().sort_index()
    in_session = hours[(hours.index >= 3) & (hours.index <= 10)].sum()
    print(f"  Bars in NSE session (03-10 UTC): {in_session} / {len(df)}")


def main() -> None:
    for symbol_dir in sorted(DATA_DIR.glob("*_NS")):
        print(f"\n{'#' * 70}")
        print(f"#  {symbol_dir.name}")
        print(f"{'#' * 70}")
        for parquet in sorted(symbol_dir.glob("*/*.parquet")):
            inspect(parquet)


if __name__ == "__main__":
    main()
    