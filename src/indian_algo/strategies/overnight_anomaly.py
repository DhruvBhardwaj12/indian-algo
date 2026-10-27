"""Overnight Return Anomaly.

Captures the structural drift that occurs while the Indian market is closed.
Buy at 3:15 PM IST, Sell at 9:15 AM IST next day.
"""

from __future__ import annotations
import pandas as pd
from indian_algo.backtesting.intraday_simulator import Trade

def _is_market_close(ts) -> bool:
    # 3:15 PM IST (Market closes at 3:30 PM)
    ist = ts.tz_convert("Asia/Kolkata")
    return (ist.hour == 15) and (ist.minute >= 15)

def _is_market_open(ts) -> bool:
    # 9:15 AM IST
    ist = ts.tz_convert("Asia/Kolkata")
    return (ist.hour == 9) and (ist.minute >= 15)

def overnight_anomaly_strategy(bars: pd.DataFrame, notional: float = 100_000.0):
    """bars is a single day's data. We want to exit at open and enter at close."""
    
    # We need at least 2 bars (one for open, one for close)
    if len(bars) < 2:
        return None
        
    # 1. Exit at Market Open (9:15 AM)
    # In reality, we sold yesterday's close. 
    # But since our simulator processes day-by-day, we can simulate the overnight PnL here.
    
    # Get the first bar of the day (Open) and the last bar of the day (Close)
    open_bar = bars.iloc[0]
    close_bar = bars.iloc[-1]
    
    entry_price = float(close_bar["close"]) # Buy at today's close
    exit_price = float(open_bar["open"])    # Sell at next day's open
    
    # NOTE: This requires a slight modification to our simulator to hold overnight.
    # Since our simulator is intraday-only, we will calculate the return of the gap.
    # The return is (Tomorrow_Open / Today_Close) - 1.
    # But wait, within a single day's dataframe, we only have today.
    
    return None # We need a continuous simulator for this!
