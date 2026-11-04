"""Backtest Multi-Symbol Panic Bounce with Macro Kill Switch."""

from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf

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

def main() -> None:
    print("Downloading data (Stocks + Nifty + VIX) over 2 years...")
    
    tickers = SYMBOLS + ["^NSEI", "^INDIAVIX"]
    data = yf.download(tickers, period="2y", interval="1d", group_by='ticker', progress=False)
    
    # Prepare Macro Data
    nifty_df = data["^NSEI"].dropna().reset_index()
    nifty_df["sma200"] = nifty_df["Close"].rolling(200).mean()
    nifty_df["date"] = pd.to_datetime(nifty_df["Date"]).dt.date
    
    vix_df = data["^INDIAVIX"].dropna().reset_index()
    vix_df["date"] = pd.to_datetime(vix_df["Date"]).dt.date
    
    macro_df = pd.merge(nifty_df[["date", "Close", "sma200"]], vix_df[["date", "Close"]], on="date", suffixes=("_nifty", "_vix"))
    
    all_trades = []
    
    for sym in SYMBOLS:
        df = data[sym].dropna().reset_index()
        # Rename stock columns explicitly so there are NO suffix collisions
        df = df.rename(columns={"Close": "stock_close"})
        df["date"] = pd.to_datetime(df["Date"]).dt.date
        
        # Merge macro data
        df = pd.merge(df, macro_df, on="date", how="left")
        df = df.sort_values("date").reset_index(drop=True)
        
        df["rsi"] = compute_rsi(df["stock_close"], 2)
        df["sma50"] = df["stock_close"].rolling(50).mean()
        
        in_position = False
        entry_price = 0.0
        entry_idx = 0
        
        for i in range(50, len(df)):
            row = df.iloc[i]
            price = row["stock_close"]
            rsi = row["rsi"]
            sma50 = row["sma50"]
            
            nifty_close = row["Close_nifty"]
            nifty_sma200 = row["sma200"]
            vix = row["Close_vix"]
            
            if pd.isna(rsi) or pd.isna(sma50) or pd.isna(nifty_sma200) or pd.isna(vix):
                continue
                
            if not in_position:
                # MACRO KILL SWITCH
                macro_ok = (nifty_close > nifty_sma200) and (vix < 25.0)
                
                if rsi < 10 and price > sma50 and macro_ok:
                    in_position = True
                    entry_price = price
                    entry_idx = i
            else:
                days_held = i - entry_idx
                if rsi > 60 or days_held >= 4:
                    ret = (price - entry_price) / entry_price
                    if ret > 0:
                        option_ret = ret * 1.5 * OPTION_LEVERAGE
                    else:
                        option_ret = ret * OPTION_LEVERAGE
                        
                    option_ret -= 0.01 # Slippage
                    pnl = INITIAL_EQUITY * option_ret
                    
                    max_premium = INITIAL_EQUITY * 0.05
                    if pnl < -max_premium:
                        pnl = -max_premium
                        
                    all_trades.append({
                        "symbol": sym, "entry": df.iloc[entry_idx]["date"], "exit": row["date"],
                        "days": days_held, "pnl": pnl
                    })
                    in_position = False

    if not all_trades:
        print("No trades generated.")
        return
        
    tdf = pd.DataFrame(all_trades)
    wins = tdf[tdf["pnl"] > 0]
    
    print(f"\n{'=' * 70}")
    print(f"  PANIC BOUNCE + MACRO KILL SWITCH (Nifty > 200SMA AND VIX < 25)")
    print(f"{'=' * 70}\n")
    print(f"  Total Trades:    {len(tdf)}")
    print(f"  Win Rate:        {len(wins)/len(tdf):.1%}")
    print(f"  Total P&L:       ₹{tdf['pnl'].sum():+,.0f}")
    print(f"  Best Trade:      ₹{tdf['pnl'].max():+,.0f}")
    print(f"  Worst Trade:     ₹{tdf['pnl'].min():+,.0f}")
    
    tdf["entry"] = pd.to_datetime(tdf["entry"])
    weeks = (tdf["entry"].max() - tdf["entry"].min()).days / 7
    print(f"  Trades per week: {len(tdf) / weeks:.1f}")

if __name__ == "__main__":
    main()
    