"""Master Scanner: RSI-2 Panic Bounce on Top 10 Indian Stocks."""

from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date

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

def main() -> None:
    print(f"\n{'=' * 70}")
    print(f"  LIVE MARKET SCANNER — {date.today()}")
    print(f"{'=' * 70}\n")
    
    vix = yf.Ticker("^INDIAVIX").history(period="1d")
    if vix.empty:
        print("Error: Could not fetch VIX.")
        return
    current_vix = vix['Close'].iloc[-1]
    print(f"  Current India VIX: {current_vix:.2f}")
    
    if current_vix > 18:
        print("  [MACRO ALERT] VIX is elevated (>18). Panic conditions. Bounces are highly likely.")
    elif current_vix < 13:
        print("  [MACRO ALERT] VIX is low (<13). Complacency. Watch for sudden drops.")
    else:
        print("  [MACRO ALERT] VIX is neutral. No macro panic.")
        
    print(f"\n  Scanning Top 10 Stocks for RSI-2 < 10...")
    print(f"  {'Symbol':<15} | {'Price':<10} | {'RSI-2':<6} | {'50 SMA':<10} | Signal")
    print("-" * 65)
    
    data = yf.download(SYMBOLS, period="1y", interval="1d", group_by='ticker')
    
    signals = []
    for sym in SYMBOLS:
        if sym not in data:
            continue
            
        df = data[sym].dropna()
        if len(df) < 50:
            continue
            
        df["rsi"] = compute_rsi(df["Close"], 2)
        df["sma50"] = df["Close"].rolling(50).mean()
        
        last_row = df.iloc[-1]
        price = last_row['Close']
        rsi = last_row['rsi']
        sma50 = last_row['sma50']
        
        signal = "WAIT"
        
        if rsi < 10 and price > sma50:
            signal = "BUY CALL (Panic Bounce)"
            signals.append(sym)
        elif rsi > 90 and price < sma50:
            signal = "BUY PUT (Complacency Drop)"
            signals.append(sym)
            
        print(f"  {sym:<15} | {price:<10.2f} | {rsi:<6.1f} | {sma50:<10.2f} | {signal}")
        
    print(f"\n{'=' * 70}")
    if signals:
        print(f"  ACTION REQUIRED: {len(signals)} setup(s) found: {', '.join(signals)}")
    else:
        print("  No setups found today. Check again tomorrow.")
    print(f"{'=' * 70}\n")

if __name__ == "__main__":
    main()
    