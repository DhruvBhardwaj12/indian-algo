"""IND-006: Multi-Symbol Auto Paper Trader (Baseline Version).

Runs daily at 3:15 PM IST.
1. Downloads historical daily data via yfinance to calculate RSI(2).
2. If RSI < 10 and Price > 50 SMA, fetches live NSE Ask price via indiaopt.
3. Simulates buying the ATM Call with a strict 20% max risk per trade.
4. Manages exits (RSI > 60, 4 days held, or 50% premium stop-loss).
"""

import time
import json
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import numpy as np
import yfinance as yf
import pytz
import asyncio
from indiaopt import NSEClient
import traceback

STATE_FILE = Path("research/paper_trading/multi_auto_state.json")
INITIAL_EQUITY = 50000.0
MAX_RISK_PER_TRADE = 0.20
PREMIUM_STOP_LOSS = 0.50

UNIVERSE = {
    "NIFTY": ("^NSEI", 75),
    "BANKNIFTY": ("^NSEBANK", 35),
    "RELIANCE": ("RELIANCE.NS", 250),
    "HDFCBANK": ("HDFCBANK.NS", 550),
    "INFY": ("INFY.NS", 400),
    "TCS": ("TCS.NS", 175),
    "SBIN": ("SBIN.NS", 750),
    "BAJFINANCE": ("BAJFINANCE.NS", 125),
    "AXISBANK": ("AXISBANK.NS", 625),
    "SUNPHARMA": ("SUNPHARMA.NS", 350),
    "MARUTI": ("MARUTI.NS", 50),
    "TITAN": ("TITAN.NS", 175),
    "BHARTIARTL": ("BHARTIARTL.NS", 475),
    "LT": ("LT.NS", 150),
    "ITC": ("ITC.NS", 1600)
}

def compute_rsi(series: pd.Series, period: int = 2) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"equity": INITIAL_EQUITY, "open_positions": [], "closed_trades": []}

async def get_live_premium(symbol: str, target_strike: float, action: str = "ask"):
    try:
        async with NSEClient() as nse:
            result = await nse.fetch_option_chain(symbol)
            for row in result.atm_window(n=30):
                if row.strike == target_strike:
                    if action == "ask":
                        return row.call_ask or row.call_ltp
                    else:
                        return row.call_bid or row.call_ltp
    except Exception as e:
        print(f"[ERROR] Failed to fetch live data for {symbol}: {e}")
        return None

async def run_daily_cycle():
    print("\n" + "="*50)
    print("Running IND-006 (Baseline Panic Bounce)...")
    print("="*50)
    
    state = load_state()
    today = date.today()
    
    print("Downloading market data...")
    tickers = [v[0] for v in UNIVERSE.values()]
    data = yf.download(tickers, period="1y", interval="1d", group_by='ticker', progress=False)
    
    # 1. Check for Exits
    open_positions = []
    for pos in state["open_positions"]:
        sym = pos["symbol"]
        ticker = UNIVERSE[sym][0]
        entry_date = datetime.strptime(pos["entry_date"], "%Y-%m-%d").date()
        days_held = (today - entry_date).days
        
        df = data[ticker].dropna()
        df["rsi"] = compute_rsi(df["Close"], 2)
        current_rsi = float(df["rsi"].iloc[-1])
        
        current_premium = await get_live_premium(sym, pos["strike"], action="bid")
        if current_premium is None:
            current_premium = pos["entry_price"]
            
        premium_drop = (current_premium - pos["entry_price"]) / pos["entry_price"]
        
        exit_time = (days_held >= 4)
        exit_rsi = (current_rsi > 60)
        exit_stop_loss = (premium_drop <= -PREMIUM_STOP_LOSS)
        
        if exit_time or exit_rsi or exit_stop_loss:
            reason = "TIME" if exit_time else ("RSI" if exit_rsi else "STOP_LOSS")
            print(f"[EXIT - {reason}] {sym} | Premium: ₹{current_premium:.2f}")
            
            pnl = (current_premium - pos["entry_price"]) * pos["lots"] * pos["lot_size"]
            state["equity"] += pnl
            state["closed_trades"].append({
                "symbol": sym, "entry_date": pos["entry_date"], "exit_date": str(today),
                "lots": pos["lots"], "entry_price": pos["entry_price"], "exit_price": current_premium,
                "pnl": round(pnl, 2), "reason": reason
            })
            print(f"[EXIT] {sym} | New Equity: ₹{state['equity']:.2f}")
        else:
            open_positions.append(pos)
            
    state["open_positions"] = open_positions
    
    # 2. Check for Entries
    print("Scanning for RSI < 10 signals...")
    for sym, (ticker, lot_size) in UNIVERSE.items():
        if any(p["symbol"] == sym for p in state["open_positions"]):
            continue
            
        df = data[ticker].dropna()
        if len(df) < 50:
            continue
            
        df["rsi"] = compute_rsi(df["Close"], 2)
        df["sma50"] = df["Close"].rolling(50).mean()
        
        last = df.iloc[-1]
        rsi_val = float(last["rsi"])
        
        print(f"  {sym:<10} | RSI: {rsi_val:.1f}")
        
        if rsi_val < 10 and last["Close"] > last["sma50"]:
            print(f"[SIGNAL] PANIC on {sym}! Fetching live Ask price...")
            
            try:
                async with NSEClient() as nse:
                    result = await nse.fetch_option_chain(sym)
                    atm_strike = result.atm_strike
            except Exception:
                atm_strike = None
                
            if atm_strike:
                ask_price = await get_live_premium(sym, atm_strike, action="ask")
                
                if ask_price:
                    cost_per_lot = ask_price * lot_size
                    max_allocation = state["equity"] * MAX_RISK_PER_TRADE
                    max_lots = int(max_allocation // cost_per_lot)
                    
                    if max_lots >= 1:
                        total_cost = max_lots * cost_per_lot
                        state["open_positions"].append({
                            "symbol": sym, "strike": atm_strike, "entry_date": str(today),
                            "entry_price": ask_price, "lots": max_lots, "lot_size": lot_size,
                            "cost": total_cost
                        })
                        print(f"[BUY] {max_lots} lot(s) of {sym} {atm_strike} CE at Ask ₹{ask_price:.2f}")
                    else:
                        print(f"[SKIP] {sym} 1 lot costs ₹{cost_per_lot:.2f}, exceeds 20% limit.")

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def main():
    print("IND-006 Baseline Auto-Trader Started.")
    try:
        asyncio.run(run_daily_cycle())
    except Exception as e:
        print(f"\n[CRASH] {e}")
        traceback.print_exc()
    
    print("Entering sleep mode. Will wake up at 3:15 PM IST on weekdays.")
    IST = pytz.timezone('Asia/Kolkata')
    
    while True:
        now = datetime.now(IST)
        if now.weekday() < 5 and now.hour == 15 and now.minute >= 15:
            if not hasattr(main, "last_run") or main.last_run != now.date():
                asyncio.run(run_daily_cycle())
                main.last_run = now.date()
        time.sleep(60)

if __name__ == "__main__":
    main()
