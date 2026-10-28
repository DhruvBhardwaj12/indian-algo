"""Build a daily PCR (Put-Call Ratio) dataset from NSE Bhavcopy.

Downloads historical Bhavcopy for the last 1 year, calculates PCR,
and saves it as a single parquet file.
"""

from __future__ import annotations
import os
import time
from pathlib import Path
from datetime import date, timedelta
import pandas as pd
from loguru import logger
import sys

# Ensure fetch_bhavcopy is importable
sys.path.insert(0, str(Path(__file__).parent))
from fetch_bhavcopy import fetch_bhavcopy

OUT_DIR = Path("data/processed")
OUT_FILE = OUT_DIR / "pcr_daily.parquet"

def main() -> None:
    print("Building PCR dataset. This will download ~250 days of data and may take 3-5 minutes...")
    
    # Get the last 365 calendar days (approx 250 trading days)
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    
    current = start_date
    rows = []
    
    while current <= end_date:
        # Skip weekends
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue
            
        date_str = current.strftime("%Y-%m-%d")
        
        # Check if we already have it cached from the IV Crush tests
        cache_path = Path(f"data/raw/options_raw/{date_str}/bhavcopy.parquet")
        
        if not cache_path.exists():
            try:
                df = fetch_bhavcopy(date_str)
                if df is not None:
                    nifty = df[(df['TckrSymb'] == 'NIFTY') & (df['OptnTp'].isin(['CE', 'PE']))].copy()
                    os.makedirs(cache_path.parent, exist_ok=True)
                    nifty.to_parquet(cache_path, index=False)
                    # Be polite to NSE to avoid rate limiting
                    time.sleep(0.5)
            except Exception as e:
                # Holiday or missing file
                current += timedelta(days=1)
                continue
                
        if cache_path.exists():
            nifty = pd.read_parquet(cache_path)
            
            # Filter for nearest expiry only (to get current sentiment)
            if not nifty.empty:
                expiries = sorted(nifty['XpryDt'].unique())
                if expiries:
                    nearest = expiries[0]
                    near_df = nifty[nifty['XpryDt'] == nearest]
                    
                    put_oi = near_df[near_df['OptnTp'] == 'PE']['OpnIntrst'].sum()
                    call_oi = near_df[near_df['OptnTp'] == 'CE']['OpnIntrst'].sum()
                    
                    pcr = put_oi / call_oi if call_oi > 0 else 0
                    
                    rows.append({
                        "date": current,
                        "pcr": pcr,
                        "put_oi": put_oi,
                        "call_oi": call_oi
                    })
                    
        current += timedelta(days=1)
        
    if not rows:
        print("No data collected.")
        return
        
    df_out = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df_out.to_parquet(OUT_FILE, index=False)
    print(f"\nSaved {len(df_out)} days of PCR data to {OUT_FILE}")
    print(df_out.tail())

if __name__ == "__main__":
    main()
    