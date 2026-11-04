"""IND-016: 15-Minute Nifty Opening Range Breakout (1 Trade/Day)."""

import pandas as pd
import numpy as np
import yfinance as yf

INITIAL_EQUITY = 50000.0
RISK_PER_TRADE = 0.10 

def main():
    print("Downloading Nifty 15m data (last 60 days)...")
    ticker = yf.Ticker("^NSEI")
    df = ticker.history(period="60d", interval="15m")
    
    if df.empty:
        print("No data found.")
        return
        
    df = df.reset_index()
    df.rename(columns={"index": "Datetime"}, inplace=True)
    
    if df["Datetime"].dt.tz is None:
        df["Datetime"] = df["Datetime"].dt.tz_localize("UTC")
    df["Datetime"] = df["Datetime"].dt.tz_convert("Asia/Kolkata")
    
    df["date"] = df["Datetime"].dt.date
    df["time"] = df["Datetime"].dt.time
    
    all_trades = []
    
    for day, day_df in df.groupby("date"):
        day_df = day_df.copy().reset_index(drop=True)
        
        # 1. Define Opening Range (9:15 - 9:30)
        opening_range = day_df.iloc[:1] # First 15m candle
        if len(opening_range) < 1: continue
        
        or_high = opening_range["High"].max()
        or_low = opening_range["Low"].min()
        range_size = or_high - or_low
        
        in_position = False
        entry_price = 0.0
        stop_price = 0.0
        target_price = 0.0
        
        # 2. Look for breakout
        for i in range(1, len(day_df)):
            row = day_df.iloc[i]
            price = row["Close"]
            time = row["time"]
            
            if not in_position:
                # Breakout above OR High
                if row["Close"] > or_high:
                    in_position = True
                    entry_price = price
                    stop_price = or_low
                    target_price = entry_price + (3 * range_size) # 3:1 R:R
            else:
                # Exit conditions
                exit_reason = None
                exit_price = 0.0
                
                if row["High"] >= target_price:
                    exit_price = target_price
                    exit_reason = "TARGET"
                elif row["Low"] <= stop_price:
                    exit_price = stop_price
                    exit_reason = "STOP"
                elif time.hour == 15 and time.minute >= 15:
                    exit_price = price
                    exit_reason = "EOD"
                    
                if exit_reason:
                    # Option multiplier: 1% Nifty move = 40% option move
                    # So 0.5% Nifty move = 20% option move
                    nifty_ret = (exit_price - entry_price) / entry_price
                    option_ret = nifty_ret * 40.0 
                    
                    pnl = INITIAL_EQUITY * RISK_PER_TRADE * option_ret
                    
                    all_trades.append({
                        "date": day, "reason": exit_reason, "nifty_ret": nifty_ret, "pnl": pnl
                    })
                    in_position = False
                    break # ONLY 1 TRADE PER DAY

    if not all_trades:
        print("No trades generated.")
        return
        
    tdf = pd.DataFrame(all_trades)
    wins = tdf[tdf["pnl"] > 0]
    
    print(f"\n{'=' * 70}")
    print(f"  IND-016: NIFTY 15-MIN ORB (1 Trade/Day)")
    print(f"{'=' * 70}\n")
    print(f"  Total Trades:    {len(tdf)}")
    print(f"  Win Rate:        {len(wins)/len(tdf):.1%}")
    print(f"  Total P&L:       ₹{tdf['pnl'].sum():+,.0f}")
    print(f"  Best Trade:      ₹{tdf['pnl'].max():+,.0f}")
    print(f"  Worst Trade:     ₹{tdf['pnl'].min():+,.0f}")
    
    print(f"\n  --- Exit Reasons ---")
    print(tdf["reason"].value_counts().to_string())
    
    tdf["date"] = pd.to_datetime(tdf["date"])
    weeks = (tdf["date"].max() - tdf["date"].min()).days / 7
    print(f"\n  Trades per week: {len(tdf) / weeks:.1f}")

if __name__ == "__main__":
    main()
    