"""Backtest Weekly Theta Farm (Monday to Wednesday Iron Condor)."""

from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
from loguru import logger
import sys

# Ensure fetch_bhavcopy is importable
sys.path.insert(0, str(Path(__file__).parent))
from fetch_bhavcopy import fetch_bhavcopy

LOT_SIZE = 50
COST_PER_LEG_BPS = 5.0

# Test 4 random weeks in 2024 (Monday to Wednesday)
WEEKS = [
    ("2024-03-04", "2024-03-06"), # Monday, Wednesday
    ("2024-06-10", "2024-06-12"),
    ("2024-09-09", "2024-09-11"),
    ("2024-11-11", "2024-11-13"),
]

def load_and_filter(date_str: str, expiry_date: str) -> pd.DataFrame | None:
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
        
    # For weekly, we want the nearest expiry (which should be Thursday)
    expiries = sorted(nifty['XpryDt'].unique())
    valid = [e for e in expiries if e >= expiry_date]
    if not valid: return None
    target = valid[0]
    
    nifty = nifty[nifty['XpryDt'] == target].copy()
    nifty = nifty[nifty['ClsPric'] > 0]
    return nifty

def get_spot_price(df: pd.DataFrame) -> float:
    # We don't have the spot price directly in F&O bhavcopy, 
    # so we approximate ATM by finding where CE and PE are closest.
    ce = df[df['OptnTp'] == 'CE'].set_index('StrkPric')['ClsPric']
    pe = df[df['OptnTp'] == 'PE'].set_index('StrkPric')['ClsPric']
    common = ce.index.intersection(pe.index)
    diff = (ce.loc[common] - pe.loc[common]).abs()
    return float(diff.idxmin())

def get_premium(df: pd.DataFrame, strike: float, opt_type: str) -> float:
    row = df[(df['StrkPric'] == strike) & (df['OptnTp'] == opt_type)]
    if row.empty: return 0.0
    return float(row['ClsPric'].iloc[0])

def run_week(t1_date: str, t2_date: str) -> dict | None:
    df_t1 = load_and_filter(t1_date, t1_date)
    df_t2 = load_and_filter(t2_date, t1_date)
    
    if df_t1 is None or df_t2 is None:
        return None

    spot = get_spot_price(df_t1)
    atm = round(spot / 50) * 50

    # We need the 50 SMA. Since we don't have historical index data in this
    # script, we will approximate the trend using the ATM Call vs Put skew.
    # If Call > Put, market is bullish. If Put > Call, market is bearish.
    atm_ce = get_premium(df_t1, atm, 'CE')
    atm_pe = get_premium(df_t1, atm, 'PE')
    
    is_uptrend = atm_ce > atm_pe

    if is_uptrend:
        # BULL PUT SPREAD
        short_strike = round(atm * 0.985 / 50) * 50 # Sell 1.5% OTM Put
        wing_strike = round(atm * 0.97 / 50) * 50   # Buy 3% OTM Put
        
        sell_prem = get_premium(df_t1, short_strike, 'PE')
        buy_wing_prem = get_premium(df_t1, wing_strike, 'PE')
        
        buy_back = get_premium(df_t2, short_strike, 'PE')
        sell_wing = get_premium(df_t2, wing_strike, 'PE')
        
        strategy = "Bull Put"
        
    else:
        # BEAR CALL SPREAD
        short_strike = round(atm * 1.015 / 50) * 50 # Sell 1.5% OTM Call
        wing_strike = round(atm * 1.03 / 50) * 50   # Buy 3% OTM Call
        
        sell_prem = get_premium(df_t1, short_strike, 'CE')
        buy_wing_prem = get_premium(df_t1, wing_strike, 'CE')
        
        buy_back = get_premium(df_t2, short_strike, 'CE')
        sell_wing = get_premium(df_t2, wing_strike, 'CE')
        
        strategy = "Bear Call"

    if sell_prem == 0 or buy_wing_prem == 0: return None

    premium_in = sell_prem - buy_wing_prem
    cost_out = buy_back - sell_wing
    
    pnl_gross = (premium_in - cost_out) * LOT_SIZE
    
    # Costs
    turnover = (sell_prem + buy_wing_prem + buy_back + sell_wing) * LOT_SIZE
    pnl_net = pnl_gross - (turnover * (COST_PER_LEG_BPS / 10000))
    
    return {
        "week": t1_date,
        "strategy": strategy,
        "atm": atm,
        "short_strike": short_strike,
        "premium_in": premium_in,
        "cost_out": cost_out,
        "pnl_net": pnl_net
    }

def main():
    print(f"\n{'=' * 80}")
    print(f"  WEEKLY THETA FARM — Monday to Wednesday")
    print(f"{'=' * 80}\n")
    
    results = []
    for t1, t2 in WEEKS:
        print(f"Testing week of {t1}...")
        res = run_week(t1, t2)
        if res:
            results.append(res)
            
    if not results:
        print("No valid trades generated.")
        return
        
    df = pd.DataFrame(results)
    print(f"\n  Trade Details:")
    print(df.to_string(index=False))

    pnls = df['pnl_net']
    wins = df[pnls > 0]
    
    print(f"\n  --- RESULTS ---")
    print(f"  Total Weeks:   {len(df)}")
    print(f"  Win Rate:      {len(wins)/len(df):.1%}")
    print(f"  Total P&L:     ₹{pnls.sum():+,.0f}")
    print(f"  Avg per Week:  ₹{pnls.mean():+,.0f}")
    print(f"  Best Week:     ₹{pnls.max():+,.0f}")
    print(f"  Worst Week:    ₹{pnls.min():+,.0f}")

if __name__ == "__main__":
    main()
