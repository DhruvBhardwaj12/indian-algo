"""Backtest Nifty vs BankNifty Stat Arb."""

from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from indian_algo.backtesting.pairs_simulator import CostModel, run_pairs_backtest
from indian_algo.strategies.index_stat_arb import index_stat_arb_strategy

DATA_DIR = Path("data/raw/nse/indices")
INITIAL_EQUITY = 20_000.0
NOTIONAL_PER_LEG = 50_000.0  # Total exposure 1L
COST_BPS_PER_SIDE = 2.5  # 5 bps RT

def _load_index(name: str, interval: str, period: str) -> pd.DataFrame | None:
    p = DATA_DIR / name / interval / f"{period}.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p)

def main() -> None:
    df_n = _load_index("NIFTY50", "15m", "60d")
    df_b = _load_index("BANKNIFTY", "15m", "60d")

    if df_n is None or df_b is None:
        print("Missing data. Run fetch_index_data.py first.")
        return

    cost = CostModel(cost_bps_per_side=COST_BPS_PER_SIDE)
    
    trades, daily_rets = run_pairs_backtest(
        df_nifty=df_n,
        df_banknifty=df_b,
        strategy_fn=lambda b: index_stat_arb_strategy(b, notional=NOTIONAL_PER_LEG),
        cost_model=cost,
        initial_equity=INITIAL_EQUITY,
        notional_per_leg=NOTIONAL_PER_LEG,
    )

    print(f"\n{'=' * 80}")
    print(f"  NIFTY vs BANKNIFTY STAT ARB — 15m bars, 60 days")
    print(f"  Notional: ₹{NOTIONAL_PER_LEG:,.0f}/leg | Cost: {COST_BPS_PER_SIDE*2:.1f} bps RT/leg")
    print(f"{'=' * 80}\n")

    if not trades:
        print("  No trades fired.")
        return

    pnls = np.array([t.pnl_net for t in trades])
    total_pnl = pnls.sum()
    
    print(f"  Total trades:  {len(trades)}")
    print(f"  Win rate:      {(pnls > 0).mean():.1%}")
    print(f"  Total P&L:     ₹{total_pnl:+,.0f}")
    print(f"  Return on ₹20k: {total_pnl / INITIAL_EQUITY:+.1%}")
    
    if (pnls < 0).any():
        pf = pnls[pnls > 0].sum() / abs(pnls[pnls < 0].sum())
        print(f"  Profit factor: {pf:.2f}")

    # Print last 5 trades for sanity
    print(f"\n  Last 5 trades:")
    for t in trades[-5:]:
        print(f"    {t.date} | dir={t.direction:+d} | {t.exit_reason:>8s} | PnL: ₹{t.pnl_net:+.0f}")

if __name__ == "__main__":
    main()
