"""110% Realistic Backtest for Panic Bounce (Truly Corrected)."""

from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf

INITIAL_EQUITY = 20_000.0
RISK_PER_TRADE = 1000.0 # ₹1,000 max risk (5% of equity)

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
            
            # --- REALISTIC LEVERAGE MODEL ---
            # 15x leverage for ATM option
            delta_pnl = stock_ret * 15.0 
            
            # Gamma boost (capped)
            gamma_pnl = (stock_ret ** 2) * 30 if stock_ret > 0 else 0
            
            # Fixed costs
            vega_crush = -0.10 if stock_ret > 0.005 else 0
            theta_decay = -0.04 * days_held # 4% per day
            spread = -0.03
            
            option_ret = delta_pnl + gamma_pnl + vega_crush + theta_decay + spread
            
            # Cap max return at +200% (Options rarely do more in 4 days)
            if option_ret > 2.0:
                option_ret = 2.0
                
            # --- GAP RISK ---
            next_open = df.iloc[i+1]["Open"]
            if next_open < price * 0.99:
                gap_loss = ((next_open - price) / price) * 15.0
                option_ret += gap_loss 
                
            exit_time = (days_held >= 4)
            exit_rsi = (rsi > 60)
            exit_stop = (option_ret <= -0.50)
            
            if exit_time or exit_rsi or exit_stop:
                reason = "STOP" if exit_stop else ("TIME" if exit_time else "RSI")
                
                # P&L calculation based strictly on risk amount
                pnl = RISK_PER_TRADE * option_ret
                if pnl < -RISK_PER_TRADE:
                    pnl = -RISK_PER_TRADE
                    
                trades.append({
                    "symbol": symbol,
                    "entry_date": df.iloc[entry_idx]["Date"].date(),
                    "exit_date": row["Date"].date(),
                    "days": days_held,
                    "option_ret": option_ret,
                    "pnl": pnl,
                    "reason": reason
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
    print(f"  PANIC BOUNCE (TRULY REALISTIC) — RESULTS")
    print(f"{'=' * 70}\n")
    print(f"  Total Trades:    {len(tdf)}")
    print(f"  Win Rate:        {len(wins)/len(tdf):.1%}")
    print(f"  Avg Days Held:   {tdf['days'].mean():.1f}")
    print(f"  Total P&L:       ₹{tdf['pnl'].sum():+,.0f}")
    print(f"  Best Trade:      ₹{tdf['pnl'].max():+,.0f}")
    print(f"  Worst Trade:     ₹{tdf['pnl'].min():+,.0f}")
    
    print(f"\n  --- Average Option Return per Trade ---")
    print(f"  {tdf['option_ret'].mean():.2%}")

if __name__ == "__main__":
    main()
    