"""Backtest VIX + PCR Confluence Strategy."""

from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger

VIX_DIR = Path("data/raw/nse/indices/INDIAVIX/1d/2y.parquet")
NIFTY_DIR = Path("data/raw/nse/indices/NIFTY50/1d/2y.parquet")
PCR_DIR = Path("data/processed/pcr_daily.parquet")
INITIAL_EQUITY = 20_000.0

# Option leverage proxy (4x for Calls, 4x for Puts)
CALL_MULT = 4.0
PUT_MULT = -4.0

def load_data() -> pd.DataFrame:
    vix = pd.read_parquet(VIX_DIR)[["timestamp", "close"]].rename(columns={"close": "vix"})
    nifty = pd.read_parquet(NIFTY_DIR)[["timestamp", "close"]].rename(columns={"close": "nifty"})
    pcr = pd.read_parquet(PCR_DIR)[["date", "pcr"]]
    
    # Ensure all dates are just 'date' objects for merging
    vix["date"] = pd.to_datetime(vix["timestamp"]).dt.date
    nifty["date"] = pd.to_datetime(nifty["timestamp"]).dt.date
    
    # Merge
    merged = pd.merge(vix[["date", "vix"]], nifty[["date", "nifty"]], on="date")
    merged = pd.merge(merged, pcr, on="date").sort_values("date").reset_index(drop=True)
    return merged

def main() -> None:
    merged = load_data()
    print(f"Data range: {merged['date'].iloc[0]} to {merged['date'].iloc[-1]} ({len(merged)} days)")

    trades = []
    equity = INITIAL_EQUITY
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    direction = 0  # +1 = Calls, -1 = Puts

    for i in range(1, len(merged)):
        row = merged.iloc[i]
        vix_val = row["vix"]
        pcr_val = row["pcr"]
        price = row["nifty"]
        
        if not in_position:
            # PANIC BOUNCE: High VIX + Low PCR (Bearish exhaustion)
            if vix_val > 18 and pcr_val < 0.85:
                in_position = True
                entry_idx = i
                entry_price = price
                direction = 1
            
            # COMPLACENCY: Low VIX + High PCR (Bullish exhaustion)
            elif vix_val < 13 and pcr_val > 1.25:
                in_position = True
                entry_idx = i
                entry_price = price
                direction = -1
        else:
            days_held = i - entry_idx
            
            # Exit when VIX reverts to neutral (16) OR 5 days max
            vix_reverted = (direction == 1 and vix_val < 16) or (direction == -1 and vix_val > 16)
            
            if vix_reverted or days_held >= 5:
                ret = (price - entry_price) / entry_price
                mult = CALL_MULT if direction == 1 else PUT_MULT
                pnl = equity * ret * mult
                
                # Cap max loss at 10% of equity (premium paid)
                pnl = max(pnl, -equity * 0.10)
                
                equity += pnl
                trades.append({
                    "entry": merged.iloc[entry_idx]["date"],
                    "exit": row["date"],
                    "type": "CALL" if direction == 1 else "PUT",
                    "vix_in": merged.iloc[entry_idx]["vix"],
                    "vix_out": vix_val,
                    "pcr_in": merged.iloc[entry_idx]["pcr"],
                    "days": days_held,
                    "nifty_ret": ret,
                    "pnl": pnl
                })
                in_position = False

    if not trades:
        print("No trades generated.")
        return

    tdf = pd.DataFrame(trades)
    wins = tdf[tdf["pnl"] > 0]
    
    print(f"\n{'=' * 70}")
    print(f"  VIX + PCR CONFLUENCE — RESULTS")
    print(f"{'=' * 70}\n")
    print(f"  Total Trades:    {len(tdf)}")
    print(f"  Win Rate:        {len(wins)/len(tdf):.1%}")
    print(f"  Avg Days Held:   {tdf['days'].mean():.1f}")
    print(f"  Total P&L:       ₹{tdf['pnl'].sum():+,.0f}")
    print(f"  Best Trade:      ₹{tdf['pnl'].max():+,.0f}")
    print(f"  Worst Trade:     ₹{tdf['pnl'].min():+,.0f}")
    
    calls = tdf[tdf["type"] == "CALL"]
    puts = tdf[tdf["type"] == "PUT"]
    print(f"\n  --- CALLS (Panic Bounce) ---")
    print(f"  Trades:      {len(calls)}")
    print(f"  Win rate:    {(calls['pnl'] > 0).mean() if len(calls) else 0:.1%}")
    print(f"  Total P&L:   ₹{calls['pnl'].sum():+,.0f}")
    
    print(f"\n  --- PUTS (Complacency) ---")
    print(f"  Trades:      {len(puts)}")
    print(f"  Win rate:    {(puts['pnl'] > 0).mean() if len(puts) else 0:.1%}")
    print(f"  Total P&L:   ₹{puts['pnl'].sum():+,.0f}")

    print(f"\n  Last 10 trades:")
    print(tdf.tail(10).to_string(index=False))

if __name__ == "__main__":
    main()
    