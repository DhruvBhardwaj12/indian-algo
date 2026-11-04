"""IND-007: Intraday Nifty RSI-2 Mean Reversion (15m bars)."""

import pandas as pd
import numpy as np
import yfinance as yf

INITIAL_EQUITY = 20000.0
OPTION_LEVERAGE = 5.0

def compute_rsi(series: pd.Series, period: int = 2) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))

def main():
    print("Downloading Nifty 15m data (last 60 days)...")
    ticker = yf.Ticker("^NSEI")
    df = ticker.history(period="60d", interval="15m")
    
    if df.empty:
        print("No data found.")
        return
        
    df = df.reset_index()
    df["rsi"] = compute_rsi(df["Close"], 2)
    df["date"] = df["Datetime"].dt.date
    
    trades = []
    equity = INITIAL_EQUITY
    
    # Group by day to enforce EOD exit
    for day, day_df in df.groupby("date"):
        day_df = day_df.reset_index(drop=True)
        
        in_position = False
        entry_price = 0.0
        
        for i in range(len(day_df)):
            row = day_df.iloc[i]
            price = row["Close"]
            rsi = row["rsi"]
            time = row["Datetime"].time()
            
            if pd.isna(rsi):
                continue
                
            if not in_position:
                # ENTRY SIGNAL
                if rsi < 10:
                    in_position = True
                    entry_price = price
            else:
                # EXIT SIGNALS
                exit_rsi = (rsi > 60)
                exit_time = (time.hour == 15 and time.minute >= 15)
                
                if exit_rsi or exit_time:
                    ret = (price - entry_price) / entry_price
                    
                    # Realistic option multiplier
                    if ret > 0:
                        option_ret = ret * 1.2 * OPTION_LEVERAGE
                    else:
                        option_ret = ret * OPTION_LEVERAGE
                        
                    # Cost: 3% spread
                    option_ret -= 0.03 
                    
                    pnl = equity * 0.10 * option_ret # Allocate 10% of equity
                    
                    trades.append({
                        "date": day,
                        "entry_time": day_df.iloc[i-1]["Datetime"] if i > 0 else row["Datetime"],
                        "exit_time": row["Datetime"],
                        "ret": ret,
                        "pnl": pnl
                    })
                    in_position = False
                    
    if not trades:
        print("No trades generated.")
        return
        
    tdf = pd.DataFrame(trades)
    wins = tdf[tdf["pnl"] > 0]
    
    print(f"\n{'=' * 70}")
    print(f"  IND-007 (INTRADAY NIFTY MEAN REVERSION) — RESULTS")
    print(f"{'=' * 70}\n")
    print(f"  Total Trades:    {len(tdf)}")
    print(f"  Win Rate:        {len(wins)/len(tdf):.1%}")
    print(f"  Total P&L:       ₹{tdf['pnl'].sum():+,.0f}")
    print(f"  Best Trade:      ₹{tdf['pnl'].max():+,.0f}")
    print(f"  Worst Trade:     ₹{tdf['pnl'].min():+,.0f}")
    
    # Frequency
    tdf["date"] = pd.to_datetime(tdf["date"])
    weeks = (tdf["date"].max() - tdf["date"].min()).days / 7
    print(f"  Trades per week: {len(tdf) / weeks:.1f}")

if __name__ == "__main__":
    main()
    