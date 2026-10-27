"""Batch Backtest of IV Crush around major Indian market events (Fixed Expiry)."""

from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
from loguru import logger
from fetch_bhavcopy import fetch_bhavcopy

LOT_SIZE = 50
WING_WIDTH = 500
COST_PER_LEG_BPS = 5.0

# Load events dynamically from CSV
try:
    events_df = pd.read_csv("data/events.csv")
    EVENTS = list(zip(events_df["t1_date"], events_df["t2_date"]))
except FileNotFoundError:
    print("Error: data/events.csv not found. Please create it first.")
    exit(1)
    

def load_and_filter(date_str: str, event_date: str) -> pd.DataFrame | None:
    """Load raw Bhavcopy, filter for the expiry strictly AFTER the event."""
    raw_p = Path(f"data/raw/options_raw/{date_str}/bhavcopy.parquet")
    
    if not raw_p.exists():
        df = fetch_bhavcopy(date_str)
        if df is None: return None
        nifty = df[(df['TckrSymb'] == 'NIFTY') & (df['OptnTp'].isin(['CE', 'PE']))].copy()
        os.makedirs(raw_p.parent, exist_ok=True)
        nifty.to_parquet(raw_p, index=False)
    else:
        nifty = pd.read_parquet(raw_p)
        
    if nifty.empty: return None
        
    # Find the nearest expiry strictly AFTER the event date
    expiries = sorted(nifty['XpryDt'].unique())
    valid_expiries = [e for e in expiries if e > event_date]
    
    if not valid_expiries:
        return None
        
    target_expiry = valid_expiries[0]
    nifty = nifty[nifty['XpryDt'] == target_expiry].copy()
    nifty = nifty[nifty['ClsPric'] > 0] # Drop zero prices
    return nifty

def get_atm_strike(df: pd.DataFrame) -> float:
    ce = df[df['OptnTp'] == 'CE'].set_index('StrkPric')['ClsPric']
    pe = df[df['OptnTp'] == 'PE'].set_index('StrkPric')['ClsPric']
    common = ce.index.intersection(pe.index)
    if common.empty: return 0.0
    diff = (ce.loc[common] - pe.loc[common]).abs()
    return float(diff.idxmin())

def get_premium(df: pd.DataFrame, strike: float, opt_type: str) -> float:
    row = df[(df['StrkPric'] == strike) & (df['OptnTp'] == opt_type)]
    if row.empty: return -1.0
    return float(row['ClsPric'].iloc[0])

def run_event(t1_date: str, t2_date: str) -> dict | None:
    # Pass t2_date as the event_date so it only picks expiries after T2
    df_t1 = load_and_filter(t1_date, t2_date)
    df_t2 = load_and_filter(t2_date, t2_date)
    
    if df_t1 is None or df_t2 is None:
        return None

    atm = get_atm_strike(df_t1)
    if atm == 0: return None

    # T-1: Get premiums
    sell_ce = get_premium(df_t1, atm, 'CE')
    sell_pe = get_premium(df_t1, atm, 'PE')
    buy_wing_ce = get_premium(df_t1, atm + WING_WIDTH, 'CE')
    buy_wing_pe = get_premium(df_t1, atm - WING_WIDTH, 'PE')
    
    if -1.0 in [sell_ce, sell_pe, buy_wing_ce, buy_wing_pe]:
        logger.warning(f"{t2_date}: Missing legs at entry. Skipping.")
        return None
        
    net_premium_in = (sell_ce + sell_pe) - (buy_wing_ce + buy_wing_pe)
    
    # T: Get exit premiums
    buy_ce = get_premium(df_t2, atm, 'CE')
    buy_pe = get_premium(df_t2, atm, 'PE')
    sell_wing_ce = get_premium(df_t2, atm + WING_WIDTH, 'CE')
    sell_wing_pe = get_premium(df_t2, atm - WING_WIDTH, 'PE')
    
    if -1.0 in [buy_ce, buy_pe, sell_wing_ce, sell_wing_pe]:
        logger.warning(f"{t2_date}: Missing legs at exit. Skipping.")
        return None
        
    net_cost_out = (buy_ce + buy_pe) - (sell_wing_ce + sell_wing_pe)
    
    pnl_gross = (net_premium_in - net_cost_out) * LOT_SIZE
    
    turnover = (sell_ce + sell_pe + buy_wing_ce + buy_wing_pe + buy_ce + buy_pe + sell_wing_ce + sell_wing_pe) * LOT_SIZE
    cost_rupees = turnover * (COST_PER_LEG_BPS / 10000)
    
    return {
        "event_date": t2_date,
        "atm_strike": atm,
        "net_premium_in": net_premium_in,
        "net_cost_out": net_cost_out,
        "pnl_gross": pnl_gross,
        "pnl_net": pnl_gross - cost_rupees,
    }

def main():
    print(f"\n{'=' * 80}")
    print(f"  IV CRUSH BATCH BACKTEST — {len(EVENTS)} Events (Fixed Expiry)")
    print(f"{'=' * 80}\n")
    
    results = []
    for t1, t2 in EVENTS:
        res = run_event(t1, t2)
        if res:
            results.append(res)
            
    if not results:
        print("No valid trades generated.")
        return
        
    df = pd.DataFrame(results)
    pnls = df['pnl_net']
    wins = df[pnls > 0]
    losses = df[pnls <= 0]
    
    print(f"\n{'=' * 80}")
    print(f"  RESULTS")
    print(f"{'=' * 80}")
    print(f"  Total Events Tested: {len(df)}")
    print(f"  Win Rate:            {len(wins)/len(df):.1%}")
    print(f"  Total Net P&L:       ₹{pnls.sum():+,.0f}")
    print(f"  Avg Net P&L:         ₹{pnls.mean():+,.0f}")
    print(f"  Best Trade:          ₹{pnls.max():+,.0f}")
    print(f"  Worst Trade:         ₹{pnls.min():+,.0f}")
    
    if len(losses) > 0:
        pf = wins['pnl_net'].sum() / abs(losses['pnl_net'].sum())
        print(f"  Profit Factor:       {pf:.2f}")
        
    print(f"\n  Trade Details:")
    print(df[['event_date', 'atm_strike', 'net_premium_in', 'net_cost_out', 'pnl_net']].to_string(index=False))

if __name__ == "__main__":
    main()
    