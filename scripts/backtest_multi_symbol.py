"""Backtest Multi-Symbol Panic Bounce (RSI-2) on Top 10 Indian Stocks."""

from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger

INITIAL_EQUITY = 20_000.0
OPTION_LEVERAGE = 4.0

SYMBOLS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
    "TCS.NS", "BHARTIARTL.NS", "SBIN.NS", "LT.NS", "ITC.NS", "KOTAKBANK.NS"
]

def compute_rsi(series: pd.Series, period: int = 2) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))

def run_symbol(symbol: str, df: pd.DataFrame) -> list[dict]:
    # FIX: Reset index so 'Date' becomes a column instead of the index
    df = df.reset_index()
    
    df = df.sort_values("Date").reset_index(drop=True)
    df["rsi"] = compute_rsi(df["Close"], 2)
    df["sma50"] = df["Close"].rolling(50).mean()
    
    trades = []
    in_position = False
    entry_price = 0.0
    entry_idx = 0
    
    for i in range(50, len(df)):
        row = df.iloc[i]
        price = row["Close"]
        rsi = row["rsi"]
        sma50 = row["sma50"]
        
        if pd.isna(rsi) or pd.isna(sma50):
            continue
            
        if not in_position:
            # ENTRY: RSI(2) < 10 AND Price > 50 SMA
            if rsi < 10 and price > sma50:
                in_position = True
                entry_price = price
                entry_idx = i
        else:
                        # EXIT: RSI(2) > 60 OR 4 days held
            days_held = i - entry_idx
            if rsi > 60 or days_held >= 4:
                ret = (price - entry_price) / entry_price
                
                # Realistic Option Return Proxy:
                # Assume Delta 0.5, Gamma positive on wins, Theta negative on holds.
                if ret > 0:
                    # Winner: Gamma boost (1.5x the stock move)
                    option_ret = ret * 1.5 * OPTION_LEVERAGE
                else:
                    # Loser: Damped by Theta, but still loses fast
                    option_ret = ret * OPTION_LEVERAGE
                    
                # Apply 1% slippage/spread cost per round trip
                option_ret = option_ret - 0.01
                
                pnl = INITIAL_EQUITY * option_ret
                
                # Cap max loss at premium paid (5% of equity = ₹1,000)
                max_premium = INITIAL_EQUITY * 0.05
                if pnl < -max_premium:
                    pnl = -max_premium
                    

                
                trades.append({
                    "symbol": symbol,
                    "entry_date": df.iloc[entry_idx]["Date"].date(),
                    "exit_date": row["Date"].date(),
                    "days": days_held,
                    "ret": ret,
                    "pnl": pnl
                })
                in_position = False
                
    return trades

def main() -> None:
    print("Downloading daily data for top 10 stocks (2 years)...")
    data = yf.download(SYMBOLS, period="2y", interval="1d", group_by='ticker')
    
    all_trades = []
    for sym in SYMBOLS:
        if sym not in data:
            continue
        df = data[sym].dropna()
        trades = run_symbol(sym, df)
        all_trades.extend(trades)
        
    if not all_trades:
        print("No trades generated.")
        return
        
    tdf = pd.DataFrame(all_trades).sort_values("entry_date").reset_index(drop=True)
    wins = tdf[tdf["pnl"] > 0]
    
    print(f"\n{'=' * 70}")
    print(f"  MULTI-SYMBOL PANIC BOUNCE — RESULTS")
    print(f"{'=' * 70}\n")
    print(f"  Total Trades:    {len(tdf)}")
    print(f"  Win Rate:        {len(wins)/len(tdf):.1%}")
    print(f"  Avg Days Held:   {tdf['days'].mean():.1f}")
    print(f"  Total P&L:       ₹{tdf['pnl'].sum():+,.0f}")
    print(f"  Best Trade:      ₹{tdf['pnl'].max():+,.0f}")
    print(f"  Worst Trade:     ₹{tdf['pnl'].min():+,.0f}")
    
    tdf["entry_date"] = pd.to_datetime(tdf["entry_date"])
    weeks = (tdf["entry_date"].max() - tdf["entry_date"].min()).days / 7
    print(f"  Trades per week: {len(tdf) / weeks:.1f}")
    
    print(f"\n  --- Trades by Symbol ---")
    print(tdf["symbol"].value_counts().to_string())

if __name__ == "__main__":
    main()
    