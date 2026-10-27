"""Live Nifty Options Tracker — Iron Condor IV Crush Edition.

Run this on T-1 (e.g., day before US CPI) at 3:00 PM IST.
Run it again on T (day of event) at 9:30 AM IST or 3:00 PM IST.
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from indiaopt import NSEClient

# We buy wings 500 points away from ATM
WING_WIDTH = 500

async def main() -> None:
    print("Fetching NSE Option Chain...")
    try:
        async with NSEClient() as nse:
            result = await nse.fetch_option_chain("NIFTY")
            spot_price = result.spot_price
            atm_strike = result.atm_strike

            # Expand window to ensure we catch the 500-point wings
            atm_row = None
            wing_ce_row = None
            wing_pe_row = None
            
            target_wing_ce = atm_strike + WING_WIDTH
            target_wing_pe = atm_strike - WING_WIDTH

            for row in result.atm_window(n=25):
                if row.strike == atm_strike:
                    atm_row = row
                elif row.strike == target_wing_ce:
                    wing_ce_row = row
                elif row.strike == target_wing_pe:
                    wing_pe_row = row

            if not atm_row:
                print(f"Error: Could not find ATM strike {atm_strike}.")
                return

            # --- ATM Straddle Data ---
            ce_ltp = atm_row.call_ltp
            pe_ltp = atm_row.put_ltp
            ce_iv = atm_row.call_iv * 100 if atm_row.call_iv and atm_row.call_iv < 1.0 else atm_row.call_iv
            pe_iv = atm_row.put_iv * 100 if atm_row.put_iv and atm_row.put_iv < 1.0 else atm_row.put_iv
            
            straddle_premium = ce_ltp + pe_ltp

            # --- Wing Data ---
            wing_ce_ltp = wing_ce_row.call_ltp if wing_ce_row else 0.0
            wing_pe_ltp = wing_pe_row.put_ltp if wing_pe_row else 0.0
            wing_cost = wing_ce_ltp + wing_pe_ltp

            # --- Iron Condor Net Premium ---
            ic_premium = straddle_premium - wing_cost

            print(f"\n{'=' * 60}")
            print(f"  NIFTY IV CRUSH TRACKER — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
            print(f"{'=' * 60}")
            print(f"  Spot Price:     ₹{spot_price:,.2f}")
            print(f"  ATM Strike:     {atm_strike}")
            print(f"  --------------------------------------------------")
            print(f"  ATM CALL:       ₹{ce_ltp:,.2f} (IV: {ce_iv:.1f}%)")
            print(f"  ATM PUT:        ₹{pe_ltp:,.2f} (IV: {pe_iv:.1f}%)")
            print(f"  STRADDLE SELL:  ₹{straddle_premium:,.2f}")
            print(f"  --------------------------------------------------")
            if wing_ce_row and wing_pe_row:
                print(f"  WING CALL ({target_wing_ce}):  ₹{wing_ce_ltp:,.2f}")
                print(f"  WING PUT ({target_wing_pe}):   ₹{wing_pe_ltp:,.2f}")
                print(f"  WING COST:      ₹{wing_cost:,.2f}")
                print(f"  --------------------------------------------------")
                print(f"  IRON CONDOR NET PREMIUM: ₹{ic_premium:,.2f} per unit")
                print(f"  Total Premium (50 lot):  ₹{ic_premium * 50:,.2f}")
            else:
                print("  WARNING: Could not find 500-point wings. Market may have moved.")
            
            print(f"{'=' * 60}\n")

    except Exception as e:
        print(f"Error fetching data: {e}")
        print("Are you running this during market hours? (9:15 AM - 3:30 PM IST)")

if __name__ == "__main__":
    asyncio.run(main())
    