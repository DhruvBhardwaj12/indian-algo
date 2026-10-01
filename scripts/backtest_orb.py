"""ORB backtest across the 10-symbol universe.

Run:
    uv run python scripts/backtest_orb.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from indian_algo.backtesting.intraday_simulator import CostModel, run_backtest
from indian_algo.strategies.orb import orb_strategy

SYMBOLS = [
    "RELIANCE_NS", "HDFCBANK_NS", "ICICIBANK_NS", "INFY_NS",
    "TATAMOTORS_NS", "BAJFINANCE_NS", "BHARTIARTL_NS", "ADANIENT_NS",
    "SBIN_NS", "VEDL_NS",
]

DATA_DIR = Path("data/raw/nse")
INTERVAL = "15m"
PERIOD = "60d"

INITIAL_EQUITY = 20_000.0
NOTIONAL_PER_TRADE = 20_000.0
COST_BPS_PER_SIDE = 8.5    # ~17 bps round trip


def _load(symbol: str) -> pd.DataFrame | None:
    p = DATA_DIR / symbol / INTERVAL / f"{PERIOD}.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p)


def _stats_from_trades(trades: list, initial: float) -> dict:
    if not trades:
        return {"n_trades": 0}
    pnls = np.array([t.pnl_net for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    return {
        "n_trades": len(trades),
        "win_rate": float((pnls > 0).mean()),
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "profit_factor": float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else float("nan"),
        "total_pnl": float(pnls.sum()),
        "final_equity": initial + float(pnls.sum()),
        "total_return": float(pnls.sum() / initial),
        "n_target": sum(1 for t in trades if t.exit_reason == "target"),
        "n_stop": sum(1 for t in trades if t.exit_reason == "stop"),
        "n_eod": sum(1 for t in trades if t.exit_reason == "eod"),
    }


def main() -> None:
    cost = CostModel(cost_bps_per_side=COST_BPS_PER_SIDE)

    all_results = []
    all_trades = []

    for symbol in SYMBOLS:
        df = _load(symbol)
        if df is None or df.empty:
            print(f"  {symbol}: no data")
            continue

        # Filter to regular session bars only (03:45 to 10:00 UTC).
        df["_ist_hour"] = df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.hour
        df = df[(df["_ist_hour"] >= 9) & (df["_ist_hour"] < 16)].reset_index(drop=True)

        result = run_backtest(
            df=df,
            strategy_fn=lambda b: orb_strategy(b, notional=NOTIONAL_PER_TRADE),
            cost_model=cost,
            initial_equity=INITIAL_EQUITY,
            notional_per_trade=NOTIONAL_PER_TRADE,
            symbol=symbol,
        )
        stats = _stats_from_trades(result.trades, INITIAL_EQUITY)
        stats["symbol"] = symbol
        all_results.append(stats)
        all_trades.extend(result.trades)

    # Print per-symbol table.
    print(f"\n{'=' * 100}")
    print(f"  ORB Backtest — 15m bars, 60 days — {len(SYMBOLS)} symbols")
    print(f"  Notional per trade: ₹{NOTIONAL_PER_TRADE:,.0f}  |  Cost: {COST_BPS_PER_SIDE} bps/side "
          f"({2 * COST_BPS_PER_SIDE:.0f} bps round trip)")
    print(f"{'=' * 100}\n")
    print(f"  {'symbol':>15s}  {'trades':>7s}  {'win%':>6s}  {'avgW':>8s}  {'avgL':>8s}  "
          f"{'PF':>6s}  {'total ₹':>10s}  {'ret%':>7s}  {'T/S/E':>8s}")
    print(f"  {'-' * 95}")

    for r in all_results:
        if r["n_trades"] == 0:
            print(f"  {r['symbol']:>15s}  {0:>7d}")
            continue
        print(f"  {r['symbol']:>15s}  {r['n_trades']:>7d}  {r['win_rate']:>5.1%}  "
              f"{r['avg_win']:>+8.0f}  {r['avg_loss']:>+8.0f}  "
              f"{r['profit_factor']:>6.2f}  {r['total_pnl']:>+10.0f}  "
              f"{r['total_return']:>+6.1%}  "
              f"{r['n_target']}/{r['n_stop']}/{r['n_eod']:>3d}")

    # Portfolio aggregate.
    if all_trades:
        pnls = np.array([t.pnl_net for t in all_trades])
        print(f"\n  {'=' * 95}")
        print(f"  PORTFOLIO ({len(all_trades)} trades across {len(all_results)} symbols)")
        print(f"  {'=' * 95}")
        print(f"    Win rate:        {(pnls > 0).mean():.1%}")
        print(f"    Total P&L:       ₹{pnls.sum():+,.0f}")
        print(f"    Avg P&L/trade:   ₹{pnls.mean():+.2f}")
        print(f"    Profit factor:   {pnls[pnls > 0].sum() / abs(pnls[pnls < 0].sum()):.2f}"
              if (pnls < 0).any() else "    Profit factor:   inf")
        print(f"    Exit reasons:    target={sum(1 for t in all_trades if t.exit_reason=='target')} "
              f"stop={sum(1 for t in all_trades if t.exit_reason=='stop')} "
              f"eod={sum(1 for t in all_trades if t.exit_reason=='eod')}")


if __name__ == "__main__":
    main()
    