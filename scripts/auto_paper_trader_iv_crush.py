"""Automated Paper Trader for Event-Driven IV Crush (Naked & Iron Condor).

Runs continuously in the background.
- On T-1 at 3:00 PM IST: Enters the trade (records premiums).
- On T at 9:30 AM IST: Exits the trade (calculates P&L).
"""

import time
import json
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import pytz
import asyncio
from indiaopt import NSEClient
import traceback

STATE_FILE = Path("research/paper_trading/iv_crush_state.json")
INITIAL_EQUITY = 50000.0
LOT_SIZE = 75
WING_WIDTH = 500

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"equity": INITIAL_EQUITY, "open_positions": [], "closed_trades": []}

def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

async def get_live_prices(symbol="NIFTY"):
    """Fetch ATM and Wings from indiaopt."""
    try:
        async with NSEClient() as nse:
            result = await nse.fetch_option_chain(symbol)
            spot = result.spot_price
            atm = result.atm_strike
            
            target_ce_wing = atm + WING_WIDTH
            target_pe_wing = atm - WING_WIDTH
            
            atm_data = None
            wing_ce_data = None
            wing_pe_data = None
            
            for row in result.atm_window(n=25):
                if row.strike == atm: atm_data = row
                elif row.strike == target_ce_wing: wing_ce_data = row
                elif row.strike == target_pe_wing: wing_pe_data = row
                    
            if atm_data and wing_ce_data and wing_pe_data:
                return {
                    "spot": spot,
                    "atm": atm,
                    "ce": atm_data.call_ask or atm_data.call_ltp,
                    "pe": atm_data.put_ask or atm_data.put_ltp,
                    "wing_ce": wing_ce_data.call_ask or wing_ce_data.call_ltp,
                    "wing_pe": wing_pe_data.put_ask or wing_pe_data.put_ltp
                }
    except Exception as e:
        print(f"[ERROR] Failed to fetch live data: {e}")
    return None

async def run_cycle():
    now_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
    today_str = now_ist.strftime("%Y-%m-%d")
    
    state = load_state()
    
    # 1. Check for Entry (T-1 at 3:00 PM)
    if now_ist.hour == 15 and now_ist.minute <= 30:
                # Check if today is a T-1 date in our CSVs
        events = []
        for csv_file in ["data/events_monthly.csv", "data/events.csv"]:
            if Path(csv_file).exists():
                df = pd.read_csv(csv_file)
                events.extend(df.to_dict('records'))
                
        for ev in events:
            if str(ev["t1_date"]) == today_str:
                # Check if we already entered today
                if any(p["event"] == ev["event_name"] for p in state["open_positions"]):
                    continue
                    
                print(f"\n[AUTO-ENTRY] It is T-1 for {ev['event_name']}! Fetching prices...")
                prices = await get_live_prices()
                if prices:
                    naked_prem = prices["ce"] + prices["pe"]
                    ic_prem = naked_prem - (prices["wing_ce"] + prices["wing_pe"])
                    
                    state["open_positions"].append({
                        "event": ev["event_name"],
                        "t2_date": str(ev["t2_date"]),
                        "atm": prices["atm"],
                        "naked_entry": naked_prem,
                        "ic_entry": ic_prem
                    })
                    save_state(state)
                    print(f"[AUTO-ENTRY] SUCCESS. Naked: ₹{naked_prem:.2f} | IC: ₹{ic_prem:.2f}")

    # 2. Check for Exit (T at 9:30 AM)
    if now_ist.hour == 9 and now_ist.minute >= 30 and now_ist.minute <= 45:
        open_positions = []
        for pos in state["open_positions"]:
            if pos["t2_date"] == today_str:
                print(f"\n[AUTO-EXIT] It is T for {pos['event']}! Fetching prices...")
                prices = await get_live_prices()
                if prices:
                    # We assume we exit at the LTP (Mid-price for simplicity)
                    naked_exit = prices["ce"] + prices["pe"]
                    ic_exit = naked_exit - (prices["wing_ce"] + prices["wing_pe"])
                    
                    naked_pnl = (pos["naked_entry"] - naked_exit) * LOT_SIZE
                    ic_pnl = (pos["ic_entry"] - ic_exit) * LOT_SIZE
                    
                    state["closed_trades"].append({
                        "event": pos["event"],
                        "naked_entry": pos["naked_entry"],
                        "naked_exit": naked_exit,
                        "naked_pnl": round(naked_pnl, 2),
                        "ic_entry": pos["ic_entry"],
                        "ic_exit": ic_exit,
                        "ic_pnl": round(ic_pnl, 2)
                    })
                    print(f"[AUTO-EXIT] {pos['event']} | Naked PnL: ₹{naked_pnl:+.2f} | IC PnL: ₹{ic_pnl:+.2f}")
                else:
                    open_positions.append(pos) # Keep it open if fetch fails
            else:
                open_positions.append(pos)
                
        if len(state["open_positions"]) != len(open_positions):
            state["open_positions"] = open_positions
            save_state(state)

def show_next_event():
    """Reads CSVs and prints the next upcoming T-1 and T dates."""
    today = datetime.now(pytz.timezone('Asia/Kolkata')).date()
    upcoming = []
    
    for csv_file in ["data/events_monthly.csv", "data/events.csv"]:
        if Path(csv_file).exists():
            try:
                df = pd.read_csv(csv_file)
                for _, row in df.iterrows():
                    # Convert string dates to date objects
                    t1 = datetime.strptime(str(row["t1_date"]), "%Y-%m-%d").date()
                    t2 = datetime.strptime(str(row["t2_date"]), "%Y-%m-%d").date()
                    
                    if t2 >= today:
                        upcoming.append({
                            "name": row["event_name"],
                            "t1": t1,
                            "t2": t2
                        })
            except Exception as e:
                print(f"[WARNING] Could not read {csv_file}: {e}")
                
    if not upcoming:
        print("⚠️ No upcoming events found in the CSV files.")
        return
        
    # Sort by entry date
    upcoming.sort(key=lambda x: x["t1"])
    next_ev = upcoming[0]
    
    days_until = (next_ev["t1"] - today).days
    
    print("\n" + "="*50)
    print("  📅 NEXT UPCOMING EVENT")
    print("="*50)
    print(f"  Event:      {next_ev['name']}")
    print(f"  Entry (T-1): {next_ev['t1']} at 3:00 PM IST")
    print(f"  Exit  (T):   {next_ev['t2']} at 9:30 AM IST")
    if days_until == 0:
        print("  Status:     ⏳ TODAY IS ENTRY DAY! Waiting for 3:00 PM...")
    elif days_until == 1:
        print("  Status:     ⏳ TOMORROW IS ENTRY DAY")
    else:
        print(f"  Status:     Waiting... ({days_until} days until entry)")
    print("="*50 + "\n")


def main():
    print("IV CRUSH AUTO-TRADER STARTED.")
    show_next_event()
    
    print("🤖 Bot is active. Will wake up exactly at T-1 (15:00 IST) and T (09:30 IST).")
    print("Keep this window open. Press Ctrl+C to stop.\n")
    
    last_run = ""
    
    while True:
        now = datetime.now(pytz.timezone('Asia/Kolkata'))
        current_key = now.strftime("%Y-%m-%d %H:%M")
        
        # Only run the check once per minute
        if current_key != last_run:
            try:
                asyncio.run(run_cycle())
            except Exception as e:
                print(f"[CRASH] {e}")
            last_run = current_key
            
        time.sleep(10)

if __name__ == "__main__":
    main()
    