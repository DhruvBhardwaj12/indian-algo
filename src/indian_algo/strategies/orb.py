"""Opening Range Breakout (ORB).

Rule:
  1. Opening range = high/low of the first bar of the session.
  2. Entry: when a later bar breaks above (long) or below (short) the range.
  3. Stop: opposite side of the opening range.
  4. Target: 2x risk (distance from entry to stop).
  5. EOD exit: at the last bar before close.

One trade per day per symbol. No overnight positions.
"""

from __future__ import annotations

import pandas as pd

from indian_algo.backtesting.intraday_simulator import Trade


# Frozen parameters (no tuning)
OPENING_BARS = 1          # number of bars forming the opening range
TARGET_RR = 2.0           # target = 2x risk
EOD_EXIT_HOUR_UTC = 9     # exit by 9:45 UTC (bar closing 9:30-9:45)
EOD_EXIT_MINUTE_UTC = 45
NOTIONAL_DEFAULT = 20_000.0


def _bar_time_utc(ts) -> tuple[int, int]:
    ist = ts.tz_convert("Asia/Kolkata")
    return ist.hour, ist.minute


def _is_before_eod_exit(ts) -> bool:
    """Return True if bar close time is before the forced EOD exit."""
    h, m = _bar_time_utc(ts)
    return (h, m) < (15, 15)  # 3:15 PM IST


def orb_strategy(bars: pd.DataFrame, notional: float = NOTIONAL_DEFAULT):
    """Returns Trade or None for a single day."""
    if len(bars) < OPENING_BARS + 2:
        return None

    opening = bars.iloc[:OPENING_BARS]
    or_high = float(opening["high"].max())
    or_low = float(opening["low"].min())
    if or_high <= or_low:
        return None

    # Iterate bars after the opening range for a breakout.
    entry_direction = 0
    entry_bar = None
    for i in range(OPENING_BARS, len(bars)):
        bar = bars.iloc[i]
        if not _is_before_eod_exit(bar["timestamp"]):
            return None  # too late in session
        if bar["high"] > or_high:
            entry_direction = 1
            entry_bar = bar
            entry_price = or_high  # assume fill at the breakout level
            stop_price = or_low
            break
        if bar["low"] < or_low:
            entry_direction = -1
            entry_bar = bar
            entry_price = or_low
            stop_price = or_high
            break

    if entry_direction == 0 or entry_bar is None:
        return None

    risk = abs(entry_price - stop_price)
    if risk <= 0:
        return None
    target_price = entry_price + entry_direction * TARGET_RR * risk

    # Monitor for stop / target / EOD from the next bar onward.
    start_idx = bars.index.get_loc(entry_bar.name) + 1
    exit_price = None
    exit_reason = "eod"
    exit_time = None

    for i in range(start_idx, len(bars)):
        bar = bars.iloc[i]
        if entry_direction == 1:
            if bar["low"] <= stop_price:
                exit_price = stop_price
                exit_reason = "stop"
                exit_time = bar["timestamp"]
                break
            if bar["high"] >= target_price:
                exit_price = target_price
                exit_reason = "target"
                exit_time = bar["timestamp"]
                break
        else:  # short
            if bar["high"] >= stop_price:
                exit_price = stop_price
                exit_reason = "stop"
                exit_time = bar["timestamp"]
                break
            if bar["low"] <= target_price:
                exit_price = target_price
                exit_reason = "target"
                exit_time = bar["timestamp"]
                break

    if exit_price is None:
        last = bars.iloc[-1]
        exit_price = float(last["close"])
        exit_time = last["timestamp"]
        exit_reason = "eod"

    pnl_gross = entry_direction * (exit_price - entry_price) / entry_price * notional

    return Trade(
        date=str(bars.iloc[0]["timestamp"].date()),
        direction=entry_direction,
        entry_time=str(entry_bar["timestamp"]),
        entry_price=entry_price,
        exit_time=str(exit_time),
        exit_price=exit_price,
        exit_reason=exit_reason,
        pnl_gross=pnl_gross,
        pnl_net=pnl_gross,   # simulator will subtract costs
        notional=notional,
    )
    