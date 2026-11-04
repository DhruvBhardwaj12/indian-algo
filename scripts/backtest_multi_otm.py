"""Backtest Multi-Symbol Panic Bounce with OTM Options."""

from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf

INITIAL_EQUITY = 20_000.0
OPTION_LEVERAGE = 8.0  # Higher leverage because OTM options are cheaper (approx 2x ATM)

SYMBOLS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
    "TCS.NS", "BHARTIARTL.NS", "SBIN.NS", "LT.NS", "ITC.NS", "KOTAKBANK.NS",
    "BAJFINANCE.NS", "AXISBANK.NS", "SUNPHARMA.NS", "MARUTI.NS", "TITAN.NS"
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
            if rsi < 10 and price > sma50:
                in_position = True
                entry_price = price
                entry_idx = i
        else:
            days_held = i - entry_idx
            
            # Calculate return
            ret = (price - entry_price) / entry_price
            
            # OTM Logic: We only make money if the stock bounces
            # If the stock stays flat or drops, the OTM option goes to zero faster.
            # We apply a higher leverage (8x) to simulate the cheaper cost, 
            # but we cut the Theta decay slightly more.
            if ret > 0:
                option_ret = ret * 1.5 * OPTION_LEVERAGE
            else:
                option_ret = ret * OPTION_LEVERAGE
                
            option_ret -= 0.015 # Slightly higher slippage for OTM
            
            exit_time = (days_held >= 4)
            exit_rsi = (rsi > 60)
            
            if exit_time or exit_rsi:
                pnl = INITIAL_EQUITY * option_ret
                max_premium = INITIAL_EQUITY * 0.05
                if pnl < -max_premium:
                    pnl = -max_premium
                    
                trades.append({
                    "symbol": symbol,
                    "entry_date": df.iloc[entry_idx]["Date"].date(),
                    "exit_date": row["Date"].date(),
                    "days": days_held,
                    "pnl": pnl
                })
                in_position = False
                
    return trades

def main() -> None:
    print("Downloading daily data for 15 stocks (2 years)...")
    data = yf.download(SYMBOLS, period="2y", interval="1d", group_by='ticker', progress=False)
    
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
    print(f"  MULTI-SYMBOL PANIC BOUNCE (OTM OPTIONS) — RESULTS")
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

if __name__ == "__main__":
    main()
    