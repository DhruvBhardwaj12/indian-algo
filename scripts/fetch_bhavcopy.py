"""Fetch and parse NSE F&O Bhavcopy for a specific date.

Run:
    uv run python scripts/fetch_bhavcopy.py 2024-02-08
"""

from __future__ import annotations
import sys
import zipfile
import io
from datetime import datetime
import requests
import pandas as pd
from loguru import logger

def fetch_bhavcopy(date_str: str) -> pd.DataFrame | None:
    """Download and parse NSE F&O Bhavcopy for a given date (YYYY-MM-DD)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    date_nse = dt.strftime("%Y%m%d")
    
    # NSE New UDiFF Format URL
    url = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{date_nse}_F_0000.csv.zip"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    logger.info(f"Fetching Bhavcopy for {date_str}")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to download: {e}")
        return None
        
    # Unzip in memory
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        csv_name = z.namelist()[0]
        with z.open(csv_name) as f:
            df = pd.read_csv(f)
            
    return df

def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/fetch_bhavcopy.py YYYY-MM-DD")
        return
        
    date_str = sys.argv[1]
    df = fetch_bhavcopy(date_str)
    
    if df is None or df.empty:
        print("No data found.")
        return
        
    # Filter for NIFTY options
    # NSE UDiFF format uses columns like 'TckrSymb' (Symbol), 'OptnTp' (CE/PE), 'StrkPric' (Strike)
    nifty_opts = df[(df['TckrSymb'] == 'NIFTY') & (df['OptnTp'].isin(['CE', 'PE']))].copy()
    
    if nifty_opts.empty:
        print("No Nifty options found in this file.")
        print("Available symbols:", df['TckrSymb'].unique()[:10])
        return
        
    # Get the nearest expiry
    # The dates are strings like '2024-02-08'
    expiries = nifty_opts['XpryDt'].unique()
    nearest_expiry = sorted(expiries)[0]
    
    print(f"\n--- NIFTY Options for {nearest_expiry} (Fetched on {date_str}) ---")
    
    # Print the first 5 rows to see the schema
    print(nifty_opts[['TckrSymb', 'XpryDt', 'StrkPric', 'OptnTp', 'ClsPric', 'OpnIntrst']].head())
    
    # Save to local parquet
    out_dir = f"data/raw/options/{date_str}"
    import os
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/nifty_opts.parquet"
    nifty_opts.to_parquet(out_path, index=False)
    print(f"\nSaved {len(nifty_opts)} option contracts to {out_path}")

if __name__ == "__main__":
    main()
    