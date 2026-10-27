"""Backtest Overnight Return Anomaly on Nifty 50."""

from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger

DATA_DIR = Path("data/raw/nse/indices")
INITIAL_EQUITY = 20_000.0
NOTIONAL = 100_000.0
COST_BPS_RT = 7.0  # ~7 bps round trip (buy close, sell open)

def main() -> None:
    # Load 60-day 15m Nifty data
    p = DATA_DIR / "NIFTY50" / "15m" / "60d.parquet"
    if not p.exists():
        print("Missing Nifty data.")
        return
        
    df = pd.read_parquet(p)
    df["_date"] = df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.date
    
    print(f"\n{'=' * 80}")
    print(f"  OVERNIGHT RETURN ANOMALY — NIFTY 50 (60 days)")
    print(f"  Notional: ₹{NOTIONAL:,.0f} | Cost: {COST_BPS_RT} bps RT")
    print(f"{'=' * 80}\n")
    
    trades = []
    daily_pnl = []
    equity = INITIAL_EQUITY
    
    # Group by day to get Open and Close
    days = []
    for day, group in df.groupby("_date"):
        if len(group) < 2:
            continue
        open_price = float(group.iloc[0]["open"])   # 9:15 AM
        close_price = float(group.iloc[-1]["close"]) # 3:30 PM
        days.append({
            "date": day,
            "open": open_price,
            "close": close_price
        })
        
    days_df = pd.DataFrame(days).sort_values("date").reset_index(drop=True)
    
    # We buy at day T's close, and sell at day T+1's open.
    for i in range(len(days_df) - 1):
        today_close = days_df.iloc[i]["close"]
        tomorrow_open = days_df.iloc[i + 1]["open"]
        
        # Gross return of the gap
        ret = (tomorrow_open - today_close) / today_close
        pnl_gross = ret * NOTIONAL
        
        # Cost (1 round trip)
        cost = NOTIONAL * (COST_BPS_RT / 10_000)
        pnl_net = pnl_gross - cost
        
        equity += pnl_net
        trades.append({
            "date": days_df.iloc[i]["date"],
            "ret": ret,
            "pnl": pnl_net
        })
        daily_pnl.append({"date": days_df.iloc[i]["date"], "equity": equity})
        
    if not trades:
        print("No trades.")
        return

    pnls = np.array([t["pnl"] for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    
    print(f"  Total nights held: {len(trades)}")
    print(f"  Win rate:          {(pnls > 0).mean():.1%}")
    print(f"  Total P&L:         ₹{pnls.sum():+,.0f}")
    print(f"  Return on ₹20k:    {pnls.sum()/INITIAL_EQUITY:+.1%}")
    
    if len(losses) > 0 and losses.sum() != 0:
        pf = wins.sum() / abs(losses.sum())
        print(f"  Profit factor:     {pf:.2f}")
        
    print(f"\n  Last 5 nights:")
    for t in trades[-5:]:
        print(f"    {t['date']} | ret={t['ret']:+.3%} | PnL: ₹{t['pnl']:+.0f}")

if __name__ == "__main__":
    main()
    