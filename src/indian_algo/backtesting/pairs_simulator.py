"""Session-aware simulator for two-leg pairs trading."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import pandas as pd
import numpy as np
from loguru import logger

@dataclass
class SpreadTrade:
    date: str
    direction: int
    entry_time: str
    entry_nifty: float
    entry_banknifty: float
    exit_time: str
    exit_nifty: float
    exit_banknifty: float
    exit_reason: str
    pnl_gross: float
    pnl_net: float
    notional_per_leg: float

class CostModel:
    def __init__(self, cost_bps_per_side: float = 2.5):
        # 2.5 bps per side = 5 bps round trip per leg
        self.cost_fraction = cost_bps_per_side / 10_000.0
        

def _compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    up = high.diff()
    down = -low.diff()
    
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=high.index)
    
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.ewm(alpha=1/window, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/window, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1/window, adjust=False).mean() / atr
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1)
    return dx.ewm(alpha=1/window, adjust=False).mean()

def run_pairs_backtest(
    df_nifty: pd.DataFrame,
    df_banknifty: pd.DataFrame,
    strategy_fn: Callable,
    cost_model: CostModel,
    initial_equity: float = 20_000.0,
    notional_per_leg: float = 50_000.0,
    z_window: int = 20,
) -> tuple[list[SpreadTrade], pd.Series]:
    
    n = df_nifty[["timestamp", "high", "low", "close"]].rename(
        columns={"high": "nifty_high", "low": "nifty_low", "close": "nifty"}
    )
    b = df_banknifty[["timestamp", "close"]].rename(columns={"close": "banknifty"})
    
    merged = pd.merge(n, b, on="timestamp", how="inner").sort_values("timestamp").reset_index(drop=True)
    
    # 1. Calculate Features GLOBALLY
    ratio = merged["banknifty"] / merged["nifty"]
    mean = ratio.rolling(z_window).mean()
    std = ratio.rolling(z_window).std()
    merged["z_score"] = (ratio - mean) / std
    merged["adx"] = _compute_adx(merged["nifty_high"], merged["nifty_low"], merged["nifty"], 14)
    
    merged["_date"] = merged["timestamp"].dt.tz_convert("Asia/Kolkata").dt.date

    equity = initial_equity
    trades: list[SpreadTrade] = []
    daily_pnl = []

    # 2. Group by day and trade
    for day, day_df in merged.groupby("_date"):
        day_df = day_df.reset_index(drop=True)
        if len(day_df) < 5:
            daily_pnl.append({"date": str(day), "pnl": 0.0, "equity": equity})
            continue

        trade = strategy_fn(day_df)
        if trade is None:
            daily_pnl.append({"date": str(day), "pnl": 0.0, "equity": equity})
            continue

        ret_b = (trade.exit_banknifty - trade.entry_banknifty) / trade.entry_banknifty
        ret_n = (trade.exit_nifty - trade.entry_nifty) / trade.entry_nifty
        spread_ret = ret_b - ret_n

        pnl_gross = trade.direction * notional_per_leg * spread_ret
        total_cost = 4 * notional_per_leg * cost_model.cost_fraction

        trade.pnl_gross = pnl_gross
        trade.pnl_net = pnl_gross - total_cost
        equity += trade.pnl_net
        trades.append(trade)
        daily_pnl.append({"date": str(day), "pnl": trade.pnl_net, "equity": equity})

    daily_df = pd.DataFrame(daily_pnl).set_index("date")
    daily_rets = daily_df["equity"].pct_change().fillna(0.0)
    return trades, daily_rets
