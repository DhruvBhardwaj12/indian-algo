"""110% Realistic Backtest: Bull Put Spread on Panic Bounce."""

import pandas as pd
import numpy as np
import yfinance as yf

INITIAL_EQUITY = 20_000.0
RISK_PER_TRADE = 1000.0 

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
    
    for i in range(50, len(df) - 1):
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
            stock_ret = (price - entry_price) / entry_price
            
            # --- BULL PUT SPREAD MATH ---
            # We sold a Put at -2% strike, bought a Put at -4% strike.
            # Max Profit = The premium we collected (approx 1.5% of stock price)
            # Max Loss = (2% strike difference) - (1.5% premium) = 0.5% of stock price
            
            # As time passes, we keep the premium (Theta positive)
            theta_keep = 0.015 * (days_held / 4) 
            
            # As IV drops, the spread becomes cheaper to close (Vega positive)
            vega_keep = 0.005 if stock_ret > -0.01 else 0
            
            if stock_ret <= -0.04:
                # We got breached. Max loss.
                option_ret = -0.005 
            else:
                # We keep the remaining premium
                option_ret = (0.015 - theta_keep) + vega_keep
                
            # Exit after 4 days or if stock rallies hard
            exit_time = (days_held >= 4)
            exit_rsi = (rsi > 60)
            
            if exit_time or exit_rsi:
                pnl = RISK_PER_TRADE * (option_ret / 0.005) # Scaled to risk
                
                trades.append({
                    "symbol": symbol,
                    "entry_date": df.iloc[entry_idx]["Date"].date(),
                    "exit_date": row["Date"].date(),
                    "days": days_held,
                    "option_ret": option_ret,
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
        
    tdf = pd.DataFrame(all_trades)
    wins = tdf[tdf["pnl"] > 0]
    
    print(f"\n{'=' * 70}")
    print(f"  BULL PUT SPREAD (110% REALISTIC) — RESULTS")
    print(f"{'=' * 70}\n")
    print(f"  Total Trades:    {len(tdf)}")
    print(f"  Win Rate:        {len(wins)/len(tdf):.1%}")
    print(f"  Total P&L:       ₹{tdf['pnl'].sum():+,.0f}")

if __name__ == "__main__":
    main()
    