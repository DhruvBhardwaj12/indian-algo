"""IND-015: Opening Range Breakout (2:1 R:R + Trailing Stop)."""

import pandas as pd
import numpy as np
import yfinance as yf

INITIAL_EQUITY = 50000.0
RISK_PER_TRADE = 0.10 
COST_PER_TRADE = 0.0005 # 5 bps

SYMBOLS = ["ADANIENT.NS", "TATASTEEL.NS", "VEDL.NS", "YESBANK.NS", "SUZLON.NS"]

def main():
    print("Downloading 5-minute data for High-Beta stocks (last 60 days)...")
    all_trades = []
    
    for sym in SYMBOLS:
        print(f"Processing {sym}...")
        ticker = yf.Ticker(sym)
        df = ticker.history(period="60d", interval="5m")
        
        if df.empty: continue
            
        df = df.reset_index()
        df.rename(columns={"index": "Datetime"}, inplace=True)
        
        if df["Datetime"].dt.tz is None:
            df["Datetime"] = df["Datetime"].dt.tz_localize("UTC")
        df["Datetime"] = df["Datetime"].dt.tz_convert("Asia/Kolkata")
        
        df["date"] = df["Datetime"].dt.date
        df["time"] = df["Datetime"].dt.time
        
        for day, day_df in df.groupby("date"):
            day_df = day_df.copy().reset_index(drop=True)
            
            # 1. Define Opening Range (9:15 to 9:30 = first 3 candles)
            opening_range = day_df.iloc[:3]
            if len(opening_range) < 3: continue
            
            or_high = opening_range["High"].max()
            or_low = opening_range["Low"].min()
            range_size = or_high - or_low
            
            if range_size <= 0: continue
                
            in_position = False
            entry_price = 0.0
            initial_stop = 0.0
            current_stop = 0.0
            target = 0.0
            
            # 2. Look for breakout from 9:30 AM onwards
            for i in range(3, len(day_df)):
                row = day_df.iloc[i]
                price = row["Close"]
                time = row["time"]
                volume = row["Volume"]
                
                if not in_position:
                    # Breakout condition
                    if row["Close"] > or_high and volume > 100000: 
                        in_position = True
                        entry_price = price
                        initial_stop = or_low
                        current_stop = or_low
                        target = entry_price + (2 * range_size) # 2:1 R:R
                else:
                    # EXIT LOGIC
                    exit_reason = None
                    exit_price = 0.0
                    
                    # Update Trailing Stop
                    if price >= entry_price + (1.5 * range_size):
                        current_stop = entry_price + range_size # Lock in 1:1
                    elif price >= entry_price + range_size:
                        current_stop = entry_price # Move to break-even
                        
                    if row["High"] >= target:
                        exit_price = target
                        exit_reason = "TARGET"
                    elif row["Low"] <= current_stop:
                        exit_price = current_stop
                        exit_reason = "TRAILING_STOP"
                    elif time.hour >= 13: # Time Stop at 1:00 PM
                        exit_price = price
                        exit_reason = "TIME_STOP"
                    elif time.hour == 15 and time.minute >= 15:
                        exit_price = price
                        exit_reason = "EOD"
                        
                    if exit_reason:
                        ret = (exit_price - entry_price) / entry_price
                        pnl = INITIAL_EQUITY * RISK_PER_TRADE * (ret - COST_PER_TRADE)
                        
                        all_trades.append({
                            "symbol": sym, "date": day, "reason": exit_reason, "pnl": pnl
                        })
                        in_position = False

    if not all_trades:
        print("No trades generated.")
        return
        
    tdf = pd.DataFrame(all_trades)
    wins = tdf[tdf["pnl"] > 0]
    
    print(f"\n{'=' * 70}")
    print(f"  IND-015: ORB (2:1 + Trailing Stop + Time Stop)")
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
    