"""Backtest IV Crush around RBI Policy (Feb 8-9, 2024).

Loads Bhavcopy data for the day before the event (T-1) and the event day (T).
Calculates P&L for:
  1. Naked Straddle (Sell ATM CE/PE)
  2. Iron Condor (Sell ATM CE/PE, Buy OTM CE/PE)

Assumes NIFTY lot size = 50.
"""

from __future__ import annotations
import pandas as pd
from pathlib import Path
from loguru import logger

LOT_SIZE = 50
ATM_WING_WIDTH = 500  # Points away from ATM for the Iron Condor wings
COST_PER_LEG_BPS = 5.0  # 5 bps per leg (entry + exit)

def load_day(date_str: str) -> pd.DataFrame:
    p = Path(f"data/raw/options/{date_str}/nifty_opts.parquet")
    if not p.exists():
        raise FileNotFoundError(f"Missing data for {date_str}. Run fetch_bhavcopy.py first.")
    df = pd.read_parquet(p)
    # Filter for nearest expiry (assuming the data is sorted or we just take the most common)
    expiry = df['XpryDt'].mode()[0]
    df = df[df['XpryDt'] == expiry].copy()
    return df

def get_atm_strike(df: pd.DataFrame) -> float:
    """Find ATM strike by minimizing the difference between Call and Put prices."""
    ce = df[df['OptnTp'] == 'CE'].set_index('StrkPric')['ClsPric']
    pe = df[df['OptnTp'] == 'PE'].set_index('StrkPric')['ClsPric']
    
    # Align strikes
    common = ce.index.intersection(pe.index)
    diff = (ce.loc[common] - pe.loc[common]).abs()
    if diff.empty:
        raise ValueError("No overlapping strikes found.")
    return float(diff.idxmin())

def get_premium(df: pd.DataFrame, strike: float, opt_type: str) -> float:
    row = df[(df['StrkPric'] == strike) & (df['OptnTp'] == opt_type)]
    if row.empty:
        return 0.0
    return float(row['ClsPric'].iloc[0])

def main() -> None:
    print("Loading data...")
    df_t1 = load_day("2024-02-08")  # Day before RBI
    df_t2 = load_day("2024-02-09")  # RBI Day
    
    atm_strike = get_atm_strike(df_t1)
    print(f"\n{'=' * 60}")
    print(f"  IV CRUSH BACKTEST — RBI Policy Feb 9, 2024")
    print(f"  ATM Strike: {atm_strike}")
    print(f"{'=' * 60}")

    # --- 1. Naked Straddle ---
    # Sell ATM Call & Put on T-1
    sell_ce = get_premium(df_t1, atm_strike, 'CE')
    sell_pe = get_premium(df_t1, atm_strike, 'PE')
    premium_collected = sell_ce + sell_pe
    
    # Buy back on T
    buy_ce = get_premium(df_t2, atm_strike, 'CE')
    buy_pe = get_premium(df_t2, atm_strike, 'PE')
    cost_to_close = buy_ce + buy_pe
    
    pnl_gross = (premium_collected - cost_to_close) * LOT_SIZE
    # 2 legs entry, 2 legs exit = 4 legs total
    cost_rupees = premium_collected * LOT_SIZE * 2 * (COST_PER_LEG_BPS / 10000) + cost_to_close * LOT_SIZE * 2 * (COST_PER_LEG_BPS / 10000)
    pnl_net_naked = pnl_gross - cost_rupees

    print(f"\n--- 1. Naked Straddle ---")
    print(f"  Sell CE @ ₹{sell_ce:.2f} | Sell PE @ ₹{sell_pe:.2f}")
    print(f"  Premium Collected: ₹{premium_collected:.2f} per unit (₹{premium_collected * LOT_SIZE:.0f} total)")
    print(f"  Buy back CE @ ₹{buy_ce:.2f} | Buy back PE @ ₹{buy_pe:.2f}")
    print(f"  Cost to Close:     ₹{cost_to_close:.2f} per unit (₹{cost_to_close * LOT_SIZE:.0f} total)")
    print(f"  Gross P&L:         ₹{pnl_gross:+,.0f}")
    print(f"  Net P&L:           ₹{pnl_net_naked:+,.0f}")

    # --- 2. Iron Condor (Safe) ---
    # Wings: Buy ATM + 500 CE, Buy ATM - 500 PE
    wing_ce_strike = atm_strike + ATM_WING_WIDTH
    wing_pe_strike = atm_strike - ATM_WING_WIDTH
    
    # T-1: Buy wings (cost)
    buy_wing_ce = get_premium(df_t1, wing_ce_strike, 'CE')
    buy_wing_pe = get_premium(df_t1, wing_pe_strike, 'PE')
    wing_cost_entry = buy_wing_ce + buy_wing_pe
    
    # T: Sell wings (recover some cost)
    sell_wing_ce = get_premium(df_t2, wing_ce_strike, 'CE')
    sell_wing_pe = get_premium(df_t2, wing_pe_strike, 'PE')
    wing_recovery = sell_wing_ce + sell_wing_pe
    
    ic_premium_collected = premium_collected - wing_cost_entry
    ic_cost_to_close = cost_to_close - wing_recovery
    
    pnl_gross_ic = (ic_premium_collected - ic_cost_to_close) * LOT_SIZE
    
    # 4 legs entry, 4 legs exit = 8 legs total
    cost_rupees_ic = (premium_collected + wing_cost_entry) * LOT_SIZE * 2 * (COST_PER_LEG_BPS / 10000) + (cost_to_close + wing_recovery) * LOT_SIZE * 2 * (COST_PER_LEG_BPS / 10000)
    pnl_net_ic = pnl_gross_ic - cost_rupees_ic

    print(f"\n--- 2. Iron Condor (Safe) ---")
    print(f"  Wings: {wing_pe_strike} PE / {wing_ce_strike} CE")
    print(f"  Sell ATM: ₹{premium_collected:.2f} | Buy Wings: ₹{wing_cost_entry:.2f}")
    print(f"  Net Premium In: ₹{ic_premium_collected:.2f} per unit")
    print(f"  Buy back ATM: ₹{cost_to_close:.2f} | Sell Wings: ₹{wing_recovery:.2f}")
    print(f"  Net Cost Out:   ₹{ic_cost_to_close:.2f} per unit")
    print(f"  Gross P&L:      ₹{pnl_gross_ic:+,.0f}")
    print(f"  Net P&L:        ₹{pnl_net_ic:+,.0f}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
    