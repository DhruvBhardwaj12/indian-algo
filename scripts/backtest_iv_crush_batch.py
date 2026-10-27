"""Batch Backtest: Naked Straddle vs Iron Condor."""

from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
from loguru import logger

# Ensure fetch_bhavcopy is importable
import sys
sys.path.insert(0, str(Path(__file__).parent))
from fetch_bhavcopy import fetch_bhavcopy

LOT_SIZE = 50
WING_WIDTH = 500
COST_PER_LEG_BPS = 5.0

def load_and_filter(date_str: str, event_date: str) -> pd.DataFrame | None:
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
        
    expiries = sorted(nifty['XpryDt'].unique())
    valid_expiries = [e for e in expiries if e > event_date]
    
    if not valid_expiries:
        return None
        
    target_expiry = valid_expiries[0]
    nifty = nifty[nifty['XpryDt'] == target_expiry].copy()
    nifty = nifty[nifty['ClsPric'] > 0]
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
    df_t1 = load_and_filter(t1_date, t2_date)
    df_t2 = load_and_filter(t2_date, t2_date)
    
    if df_t1 is None or df_t2 is None:
        return None

    atm = get_atm_strike(df_t1)
    if atm == 0: return None

    sell_ce = get_premium(df_t1, atm, 'CE')
    sell_pe = get_premium(df_t1, atm, 'PE')
    buy_wing_ce = get_premium(df_t1, atm + WING_WIDTH, 'CE')
    buy_wing_pe = get_premium(df_t1, atm - WING_WIDTH, 'PE')
    
    if -1.0 in [sell_ce, sell_pe, buy_wing_ce, buy_wing_pe]:
        return None

    buy_ce = get_premium(df_t2, atm, 'CE')
    buy_pe = get_premium(df_t2, atm, 'PE')
    sell_wing_ce = get_premium(df_t2, atm + WING_WIDTH, 'CE')
    sell_wing_pe = get_premium(df_t2, atm - WING_WIDTH, 'PE')
    
    if -1.0 in [buy_ce, buy_pe, sell_wing_ce, sell_wing_pe]:
        return None
        
    # Naked Straddle
    naked_premium_in = sell_ce + sell_pe
    naked_cost_out = buy_ce + buy_pe
    naked_gross = (naked_premium_in - naked_cost_out) * LOT_SIZE
    naked_turnover = (sell_ce + sell_pe + buy_ce + buy_pe) * LOT_SIZE
    naked_costs = naked_turnover * (COST_PER_LEG_BPS / 10000)
    naked_net = naked_gross - naked_costs

    # Iron Condor
    ic_premium_in = naked_premium_in - (buy_wing_ce + buy_wing_pe)
    ic_cost_out = naked_cost_out - (sell_wing_ce + sell_wing_pe)
    ic_gross = (ic_premium_in - ic_cost_out) * LOT_SIZE
    ic_turnover = (sell_ce + sell_pe + buy_wing_ce + buy_wing_pe + buy_ce + buy_pe + sell_wing_ce + sell_wing_pe) * LOT_SIZE
    ic_costs = ic_turnover * (COST_PER_LEG_BPS / 10000)
    ic_net = ic_gross - ic_costs
    
    return {
        "event_date": t2_date,
        "atm_strike": atm,
        "naked_pnl": naked_net,
        "ic_pnl": ic_net
    }

def main():
    print(f"\n{'=' * 80}")
    print(f"  IV CRUSH: NAKED vs IRON CONDOR")
    print(f"{'=' * 80}\n")
    
    try:
        events_df = pd.read_csv("data/events_monthly.csv")
        EVENTS = list(zip(events_df["t1_date"], events_df["t2_date"]))
    except FileNotFoundError:
        print("Error: data/events.csv not found. Please create it first.")
        return

    results = []
    for t1, t2 in EVENTS:
        print(f"Testing {t2}...")
        res = run_event(t1, t2)
        if res:
            results.append(res)
            
    if not results:
        print("\nNo valid trades generated. (Check data files)")
        return
        
    df = pd.DataFrame(results)
    
    print(f"\n  Trade Details:")
    print(df.to_string(index=False))

    n_pnls = df['naked_pnl']
    n_wins = df[n_pnls > 0]
    print(f"\n  --- 1. NAKED STRADDLE (High Risk) ---")
    print(f"  Win Rate:      {len(n_wins)/len(df):.1%}")
    print(f"  Total P&L:     ₹{n_pnls.sum():+,.0f}")
    print(f"  Best Trade:    ₹{n_pnls.max():+,.0f}")
    print(f"  Worst Trade:   ₹{n_pnls.min():+,.0f}")
    if len(n_wins) > 0 and n_pnls.min() < 0:
        print(f"  Profit Factor: {n_wins['naked_pnl'].sum() / abs(n_pnls.min()):.2f}")

    ic_pnls = df['ic_pnl']
    ic_wins = df[ic_pnls > 0]
    print(f"\n  --- 2. IRON CONDOR (Safe) ---")
    print(f"  Win Rate:      {len(ic_wins)/len(df):.1%}")
    print(f"  Total P&L:     ₹{ic_pnls.sum():+,.0f}")
    print(f"  Best Trade:    ₹{ic_pnls.max():+,.0f}")
    print(f"  Worst Trade:   ₹{ic_pnls.min():+,.0f}")
    if len(ic_wins) > 0 and ic_pnls.min() < 0:
        print(f"  Profit Factor: {ic_wins['ic_pnl'].sum() / abs(ic_pnls.min()):.2f}")

if __name__ == "__main__":
    main()
