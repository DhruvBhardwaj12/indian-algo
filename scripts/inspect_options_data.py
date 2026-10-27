"""Stream and inspect the India Options 1-minute dataset from Hugging Face.

Does NOT download the full dataset (377M+ rows). Streams a sample,
prints the schema, and saves a small local parquet for backtesting.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from datasets import load_dataset

DATASET_NAME = "thetrademarkk/india-index-options-1m"
OUT_DIR = Path("data/raw/options_sample")


def main() -> None:
    print("Streaming dataset (this does not download everything)...")

    # Load in streaming mode to avoid pulling the entire dataset
    ds = load_dataset(DATASET_NAME, streaming=True, split="train")

    # Peek at the schema from the first row
    first = next(iter(ds))
    print("\n--- Schema ---")
    for key, value in first.items():
        print(f"  {key:>15s}: {type(value).__name__} = {value}")

    # Collect a small sample (e.g., first 5000 rows)
    print("\nCollecting sample (5000 rows)...")
    rows = []
    for i, row in enumerate(ds):
        rows.append(row)
        if i >= 4999:
            break

    df = pd.DataFrame(rows)
    print(f"\nSample shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst 3 rows:\n{df.head(3).to_string()}")
    print(f"\nUnique symbols: {df['symbol'].unique().tolist() if 'symbol' in df else 'N/A'}")
    if "option_type" in df:
        print(f"Option types: {df['option_type'].unique().tolist()}")

    # Save the sample locally for backtesting
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "sample_5000.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\nSaved sample to {out_path}")


if __name__ == "__main__":
    main()
    