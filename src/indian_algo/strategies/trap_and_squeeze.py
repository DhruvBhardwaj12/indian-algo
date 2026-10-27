"""High-Beta Trap & Squeeze.

Fades failed opening range breakouts. Logic:
  1. Define Opening Range (OR) from the first 15-min bar (9:15-9:30).
  2. For a LONG: Wait for a break below OR Low, then a close back above OR Low.
     Entry: Reclaim bar close. Stop: Fakeout low. Target: OR High.
  3. For a SHORT: Wait for a break above OR High, then a close back below OR High.
     Entry: Rejection bar close. Stop: Fakeout high. Target: OR Low.
"""

from __future__ import annotations
import pandas as pd
from indian_algo.backtesting.intraday_simulator import Trade

OPENING_BARS = 1
MAX_TRAP_BARS = 3  # Must reclaim within 3 bars of the initial break
TARGET_RR = 1.0    # Target is the opposite side of the OR, so RR is approx 1:1 or better
NOTIONAL_DEFAULT = 100_000.0 # 5x leverage on 20k

def _is_before_eod_exit(ts) -> bool:
    ist = ts.tz_convert("Asia/Kolkata")
    return (ist.hour, ist.minute) < (15, 15)

def trap_and_squeeze_strategy(bars: pd.DataFrame, notional: float = NOTIONAL_DEFAULT):
    if len(bars) < OPENING_BARS + 3:
        return None

    opening = bars.iloc[:OPENING_BARS]
    or_high = float(opening["high"].max())
    or_low = float(opening["low"].min())
    
    if or_high <= or_low:
        return None

    # Iterate to find the trap
    entry_direction = 0
    entry_bar = None
    fakeout_extreme = None
    
    for i in range(OPENING_BARS, len(bars)):
        bar = bars.iloc[i]
        if not _is_before_eod_exit(bar["timestamp"]):
            return None  # Too late

        # Check for LONG trap (breakdown then reclaim)
        if bar["low"] < or_low:
            # Look at the next few bars to see if it reclaims
            end_scan = min(i + MAX_TRAP_BARS + 1, len(bars))
            fake_low = bar["low"]
            
            for j in range(i, end_scan):
                scan_bar = bars.iloc[j]
                fake_low = min(fake_low, scan_bar["low"])
                
                # Reclaim condition: close back above OR Low
                if scan_bar["close"] > or_low and j > i:
                    entry_direction = 1
                    entry_bar = scan_bar
                    entry_price = scan_bar["close"]
                    stop_price = fake_low
                    break
            if entry_direction != 0:
                break

        # Check for SHORT trap (breakout then reject)
        if bar["high"] > or_high:
            end_scan = min(i + MAX_TRAP_BARS + 1, len(bars))
            fake_high = bar["high"]
            
            for j in range(i, end_scan):
                scan_bar = bars.iloc[j]
                fake_high = max(fake_high, scan_bar["high"])
                
                # Reject condition: close back below OR High
                if scan_bar["close"] < or_high and j > i:
                    entry_direction = -1
                    entry_bar = scan_bar
                    entry_price = scan_bar["close"]
                    stop_price = fake_high
                    break
            if entry_direction != 0:
                break

    if entry_direction == 0 or entry_bar is None:
        return None

    # Target logic
    if entry_direction == 1:
        target_price = or_high
    else:
        target_price = or_low

    # Monitor for exit
    start_idx = bars.index.get_loc(entry_bar.name) + 1
    exit_price = None
    exit_reason = "eod"
    
    for i in range(start_idx, len(bars)):
        bar = bars.iloc[i]
        if entry_direction == 1:
            if bar["low"] <= stop_price:
                exit_price = stop_price
                exit_reason = "stop"
                break
            if bar["high"] >= target_price:
                exit_price = target_price
                exit_reason = "target"
                break
        else:
            if bar["high"] >= stop_price:
                exit_price = stop_price
                exit_reason = "stop"
                break
            if bar["low"] <= target_price:
                exit_price = target_price
                exit_reason = "target"
                break

    if exit_price is None:
        exit_price = float(bars.iloc[-1]["close"])

    pnl_gross = entry_direction * (exit_price - entry_price) / entry_price * notional

    return Trade(
        date=str(bars.iloc[0]["timestamp"].date()),
        direction=entry_direction,
        entry_time=str(entry_bar["timestamp"]),
        entry_price=entry_price,
        exit_time=str(bars.iloc[-1]["timestamp"]),
        exit_price=exit_price,
        exit_reason=exit_reason,
        pnl_gross=pnl_gross,
        pnl_net=pnl_gross,
        notional=notional,
    )
