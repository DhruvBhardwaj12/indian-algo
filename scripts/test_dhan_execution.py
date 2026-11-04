"""Test Dhan Sandbox Execution Only."""

from dhanhq import dhanhq, DhanContext
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
    access_token = os.getenv("DHAN_SANDBOX_ACCESS_TOKEN", "").strip()
    
    print(f"Using Client ID ending in: ...{client_id[-4:]}")
    print(f"Using Token ending in: ...{access_token[-4:]}")
    
    dhan_context = DhanContext(client_id, access_token)
    dhan = dhanhq(dhan_context)
    # Force Sandbox URL
    dhan.base_url = "https://sandbox.dhan.co/v2"

    print("\nAttempting to place a dummy order...")
    try:
        response = dhan.place_order(
            security_id="12345", # Dummy ID
            exchange_segment=dhan.NSE_FNO,
            transaction_type=dhan.BUY,
            quantity=75,
            order_type=dhan.LIMIT,
            product_type=dhan.INTRA,
            price=100.0
        )
        print(f"Response: {response}")
        
        if response.get('status') == 'success':
            print("\n✅ SUCCESS! Dhan sandbox execution is working.")
        else:
            print("\n❌ FAILED. Read the error below:")
            print(response)
            
    except Exception as e:
        print(f"\n❌ CRASHED: {e}")

if __name__ == "__main__":
    main()
