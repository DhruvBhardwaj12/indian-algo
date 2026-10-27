"""Index Statistical Arbitrage with ADX Filter and asymmetric RR."""

from __future__ import annotations
import pandas as pd
from indian_algo.backtesting.pairs_simulator import SpreadTrade

Z_ENTRY = 2.0
Z_EXIT = 0.0      # Exit at the mean
Z_STOP = 3.0      # Hard stop if spread diverges further
ADX_THRESHOLD = 20.0

def _is_before_eod_exit(ts) -> bool:
    ist = ts.tz_convert("Asia/Kolkata")
    return (ist.hour, ist.minute) < (15, 15)

def index_stat_arb_strategy(bars: pd.DataFrame, notional: float = 50_000.0):
    for i in range(len(bars)):
        bar = bars.iloc[i]
        if not _is_before_eod_exit(bar["timestamp"]):
            return None

        zi = bar["z_score"]
        current_adx = bar["adx"]
        
        if pd.isna(zi) or pd.isna(current_adx):
            continue
            
        if current_adx > ADX_THRESHOLD:
            continue 

        direction = 0
        if zi > Z_ENTRY:
            direction = -1  # Short B, Long N
        elif zi < -Z_ENTRY:
            direction = 1   # Long B, Short N

        if direction != 0:
            entry_bar = bar
            entry_n = float(bar["nifty"])
            entry_b = float(bar["banknifty"])
            
            exit_n, exit_b = entry_n, entry_b
            exit_time = str(entry_bar["timestamp"])
            exit_reason = "eod"

            for j in range(i + 1, len(bars)):
                scan_bar = bars.iloc[j]
                scan_z = scan_bar["z_score"]
                
                exit_n = float(scan_bar["nifty"])
                exit_b = float(scan_bar["banknifty"])
                exit_time = str(scan_bar["timestamp"])

                if pd.isna(scan_z):
                    continue

                # NEW LOGIC: Stop out if it diverges, hold until mean if it reverts
                if direction == -1 and scan_z > Z_STOP:
                    exit_reason = "stop"
                    break
                if direction == 1 and scan_z < -Z_STOP:
                    exit_reason = "stop"
                    break
                    
                if direction == -1 and scan_z <= Z_EXIT:
                    exit_reason = "reverted"
                    break
                if direction == 1 and scan_z >= -Z_EXIT:
                    exit_reason = "reverted"
                    break
                    
                if not _is_before_eod_exit(scan_bar["timestamp"]):
                    exit_reason = "eod"
                    break

            return SpreadTrade(
                date=str(entry_bar["timestamp"].date()),
                direction=direction,
                entry_time=str(entry_bar["timestamp"]),
                entry_nifty=entry_n,
                entry_banknifty=entry_b,
                exit_time=exit_time,
                exit_nifty=exit_n,
                exit_banknifty=exit_b,
                exit_reason=exit_reason,
                pnl_gross=0.0,
                pnl_net=0.0,
                notional_per_leg=notional,
            )
    return None
