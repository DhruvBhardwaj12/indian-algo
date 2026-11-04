"""Live Nifty Iron Condor Tracker via Dhan API (for US CPI Event)."""

import asyncio
from datetime import datetime, timezone
from dhanhq import dhanhq, DhanContext
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()

LOT_SIZE = 75
WING_WIDTH = 500
NIFTY_SECURITY_ID = 13
NIFTY_SEGMENT = "IDX_I"

def get_dhan_client():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_SANDBOX_ACCESS_TOKEN")
    if not client_id or not access_token:
        raise ValueError("Dhan credentials not found in .env file.")
    return dhanhq(DhanContext(client_id, access_token))

def main():
    print(f"\n{'=' * 65}")
    print(f"  NIFTY IV CRUSH TRACKER (Dhan) — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'=' * 65}")
    print("Fetching live Option Chain from Dhan...")

    try:
        dhan = get_dhan_client()
        
        # 1. Get nearest expiry
        expiry_response = dhan.expiry_list(
            under_security_id=NIFTY_SECURITY_ID,
            under_exchange_segment=NIFTY_SEGMENT
        )
        if expiry_response["status"] != "success" or not expiry_response["data"]:
            print("Error: Could not fetch expiry list.")
            return
        nearest_expiry = expiry_response["data"][0]
        print(f"Nearest Expiry: {nearest_expiry}")

        # 2. Fetch option chain
        chain_response = dhan.option_chain(
            under_security_id=NIFTY_SECURITY_ID,
            under_exchange_segment=NIFTY_SEGMENT,
            expiry=nearest_expiry
        )
        if chain_response["status"] != "success":
            print(f"Error fetching option chain: {chain_response}")
            return

        oc = chain_response["data"]["oc"]
        
        # 3. Determine ATM strike (closest to spot)
        # The option chain response includes 'last_price' for the underlying
        spot_price = chain_response["data"]["last_price"]
        atm_strike = round(spot_price / 50) * 50
        target_wing_ce = atm_strike + WING_WIDTH
        target_wing_pe = atm_strike - WING_WIDTH

        atm_data = oc.get(str(atm_strike))
        wing_ce_data = oc.get(str(target_wing_ce))
        wing_pe_data = oc.get(str(target_wing_pe))

        if not atm_data or not wing_ce_data or not wing_pe_data:
            print("Error: Could not find all required strikes (ATM or wings).")
            return

        # 4. Extract premiums (using top_ask_price for conservative entry)
        ce_ltp = atm_data["ce"]["top_ask_price"] or atm_data["ce"]["last_price"]
        pe_ltp = atm_data["pe"]["top_ask_price"] or atm_data["pe"]["last_price"]
        straddle_premium = ce_ltp + pe_ltp

        wing_ce_ltp = wing_ce_data["ce"]["top_ask_price"] or wing_ce_data["ce"]["last_price"]
        wing_pe_ltp = wing_pe_data["pe"]["top_ask_price"] or wing_pe_data["pe"]["last_price"]
        wing_cost = wing_ce_ltp + wing_pe_ltp

        ic_premium = straddle_premium - wing_cost
        total_margin_required = ic_premium * LOT_SIZE

        print(f"\n  Spot Price:     ₹{spot_price:,.2f}")
        print(f"  ATM Strike:     {atm_strike}")
        print(f"  ---------------------------------------------------")
        print(f"  ATM CALL:       ₹{ce_ltp:,.2f}")
        print(f"  ATM PUT:        ₹{pe_ltp:,.2f}")
        print(f"  STRADDLE SELL:  ₹{straddle_premium:,.2f}")
        print(f"  ---------------------------------------------------")
        print(f"  WING CALL ({target_wing_ce}):  ₹{wing_ce_ltp:,.2f}")
        print(f"  WING PUT ({target_wing_pe}):   ₹{wing_pe_ltp:,.2f}")
        print(f"  WING COST:      ₹{wing_cost:,.2f}")
        print(f"  ---------------------------------------------------")
        print(f"  IRON CONDOR NET PREMIUM: ₹{ic_premium:,.2f} per unit")
        print(f"  TOTAL PREMIUM (75 lot):  ₹{total_margin_required:,.2f}")
        print(f"  ---------------------------------------------------")
        print(f"  MAX RISK (if wings breached): ₹{(WING_WIDTH - ic_premium) * LOT_SIZE:,.2f}")
        print(f"{'=' * 65}\n")

    except Exception as e:
        print("\n[WARNING] Market closed or Dhan API unreachable.")
        print("Please run this between 9:15 AM and 3:30 PM IST on a trading day.")
        print(f"Error details: {e}\n")

if __name__ == "__main__":
    main()
    