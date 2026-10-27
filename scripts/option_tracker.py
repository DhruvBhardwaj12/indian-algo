"""Live Nifty Options Tracker via indiaopt."""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from indiaopt import NSEClient

async def main() -> None:
    print("Fetching NSE Option Chain...")
    try:
        async with NSEClient() as nse:
            result = await nse.fetch_option_chain("NIFTY")
            spot_price = result.spot_price
            atm_strike = result.atm_strike

            atm_row = None
            for row in result.atm_window(n=5):
                if row.strike == atm_strike:
                    atm_row = row
                    break

            if not atm_row:
                print(f"Error: Could not find ATM strike {atm_strike} data.")
                return

            # Extract correct attributes
            call_premium = atm_row.call_ltp
            put_premium = atm_row.put_ltp
            call_iv = atm_row.call_iv
            put_iv = atm_row.put_iv
            
            # IndiaOpt usually returns IV as a percentage (e.g., 15.5) 
            # but if it's a decimal (e.g., 0.155), we adjust.
            if call_iv and call_iv < 1.0:
                call_iv *= 100
            if put_iv and put_iv < 1.0:
                put_iv *= 100

            straddle_price = call_premium + put_premium
            # Rule of thumb: Expected Move = Straddle * 0.85
            expected_move = straddle_price * 0.85
            expected_move_pct = (expected_move / spot_price) * 100
            
            print(f"\n{'=' * 60}")
            print(f"  NIFTY OPTIONS TRACKER — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
            print(f"{'=' * 60}")
            print(f"  Spot Price:     ₹{spot_price:,.2f}")
            print(f"  ATM Strike:     {atm_strike}")
            print(f"  Call Premium:   ₹{call_premium:,.2f} (IV: {call_iv:.1f}%)")
            print(f"  Put Premium:    ₹{put_premium:,.2f} (IV: {put_iv:.1f}%)")
            print(f"  --------------------------------------------------")
            print(f"  STRADDLE SELL:  ₹{straddle_price:,.2f}")
            print(f"  Implied Move:   ±₹{expected_move:,.2f} ({expected_move_pct:.2f}%)")
            print(f"  --------------------------------------------------")
            print(f"  To profit, Nifty must stay between:")
            print(f"  {spot_price - expected_move:,.2f}  and  {spot_price + expected_move:,.2f}")
            print(f"{'=' * 60}\n")

    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    asyncio.run(main())
    