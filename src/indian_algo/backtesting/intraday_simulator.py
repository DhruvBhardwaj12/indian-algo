"""Session-aware intraday backtest simulator.

Handles NSE market structure: no overnight positions, forced EOD exit.

Trade-based (not position-based). Each day is independent: strategy
receives the bars for one day and returns at most one trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from loguru import logger


@dataclass
class Trade:
    date: str
    direction: int          # +1 long, -1 short
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    exit_reason: str        # 'target', 'stop', 'eod'
    pnl_gross: float        # before costs, in INR
    pnl_net: float          # after costs
    notional: float


@dataclass
class SymbolResult:
    symbol: str
    trades: list[Trade]
    daily_returns: pd.Series
    final_equity: float
    initial_equity: float


class CostModel:
    """Intraday equity cost model for Indian discount brokers."""

    def __init__(self, cost_bps_per_side: float = 8.5):
        # Default: 8.5 bps per side = 17 bps round trip (see header of backtest).
        self.cost_fraction = cost_bps_per_side / 10_000.0

    def buy_cost(self, notional: float) -> float:
        return notional * self.cost_fraction

    def sell_cost(self, notional: float) -> float:
        return notional * self.cost_fraction


def _session_date(df: pd.DataFrame) -> pd.Series:
    """Return the NSE trading date (IST) for each UTC timestamp."""
    ist = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    return ist.dt.date


def run_backtest(
    df: pd.DataFrame,
    strategy_fn: Callable[[pd.DataFrame], Trade | None],
    cost_model: CostModel,
    initial_equity: float = 20_000.0,
    notional_per_trade: float = 20_000.0,
    symbol: str = "UNKNOWN",
) -> SymbolResult:
    """Run an intraday backtest on a single symbol.

    strategy_fn receives the bars for one day and returns a Trade
    (before costs are applied) or None.
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["_date"] = _session_date(df)

    equity = initial_equity
    trades: list[Trade] = []
    daily_pnl = []

    for day, bars in df.groupby("_date"):
        bars = bars.reset_index(drop=True)
        if len(bars) < 5:
            daily_pnl.append({"date": str(day), "pnl": 0.0, "equity": equity})
            continue

        trade = strategy_fn(bars)
        if trade is None:
            daily_pnl.append({"date": str(day), "pnl": 0.0, "equity": equity})
            continue

        # Apply costs.
        entry_cost = cost_model.buy_cost(trade.notional) if trade.direction == 1 else cost_model.sell_cost(trade.notional)
        exit_cost = cost_model.sell_cost(trade.notional) if trade.direction == 1 else cost_model.buy_cost(trade.notional)

        trade.pnl_net = trade.pnl_gross - entry_cost - exit_cost
        equity += trade.pnl_net
        trades.append(trade)

        daily_pnl.append({"date": str(day), "pnl": trade.pnl_net, "equity": equity})

    daily_df = pd.DataFrame(daily_pnl).set_index("date")
    daily_rets = daily_df["equity"].pct_change().fillna(0.0)

    return SymbolResult(
        symbol=symbol,
        trades=trades,
        daily_returns=daily_rets,
        final_equity=equity,
        initial_equity=initial_equity,
    )
