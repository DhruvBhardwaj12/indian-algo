"""Backtest Nifty 50 Mean Reversion (RSI-2) with Trend Filter."""

from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger

DATA_DIR = Path("data/raw/nse/indices/NIFTY50/1d")
INITIAL_EQUITY = 20_000.0

def compute_rsi(series: pd.Series, period: int = 2) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))

def main() -> None:
    p = DATA_DIR / "2y.parquet"
    if not p.exists():
        print("Missing Nifty daily data.")
        return
        
    df = pd.read_parquet(p)
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    # 1. Calculate Features
    df["rsi"] = compute_rsi(df["close"], 2)
    df["sma_200"] = df["close"].rolling(200).mean()
    
    trades = []
    equity = INITIAL_EQUITY
    
    in_position = False
    entry_price = 0.0
    entry_idx = 0
    
    for i in range(200, len(df)):
        row = df.iloc[i]
        ts = row["timestamp"]
        price = row["close"]
        rsi = row["rsi"]
        sma200 = row["sma_200"]
        
        if pd.isna(rsi) or pd.isna(sma200):
            continue
            
        if not in_position:
            # ENTRY: RSI(2) < 10 AND Price > 200 SMA (Uptrend only)
            if rsi < 10 and price > sma200:
                in_position = True
                entry_price = price
                entry_idx = i
        else:
            # Calculate return
            ret = (price - entry_price) / entry_price
            
            # EXIT: Take profit at +0.5%, Stop loss at -0.75%, OR 4 days held
            days_held = i - entry_idx
            if ret >= 0.005 or ret <= -0.0075 or days_held >= 4:
                
                # Option leverage proxy: 3x (accounting for Theta)
                option_leverage = 3.0
                pnl = equity * ret * option_leverage
                
                equity += pnl
                trades.append({
                    "entry_date": df.iloc[entry_idx]["timestamp"].date(),
                    "exit_date": ts.date(),
                    "days_held": days_held,
                    "nifty_ret": ret,
                    "pnl": pnl
                })
                in_position = False

    # Print results
    print(f"\n{'=' * 70}")
    print(f"  NIFTY PANIC BOUNCE (RSI-2 + Trend Filter)")
    print(f"{'=' * 70}\n")
    
    if not trades:
        print("No trades fired.")
        return
        
    tdf = pd.DataFrame(trades)
    wins = tdf[tdf["pnl"] > 0]
    
    print(f"  Total Trades:    {len(tdf)}")
    print(f"  Win Rate:        {len(wins)/len(tdf):.1%}")
    print(f"  Avg Days Held:   {tdf['days_held'].mean():.1f}")
    print(f"  Total P&L:       ₹{tdf['pnl'].sum():+,.0f}")
    print(f"  Best Trade:      ₹{tdf['pnl'].max():+,.0f}")
    print(f"  Worst Trade:     ₹{tdf['pnl'].min():+,.0f}")
    
    print(f"\n  Last 5 Trades:")
    print(tdf.tail(5).to_string(index=False))

if __name__ == "__main__":
    main()
    