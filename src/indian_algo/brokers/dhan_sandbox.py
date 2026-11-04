# src/indian_algo/brokers/dhan_sandbox.py
import os
from dotenv import load_dotenv
from dhanhq import DhanContext, dhanhq

load_dotenv()

def get_sandbox_client():
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_SANDBOX_ACCESS_TOKEN")
    if not client_id or not access_token:
        raise ValueError("Dhan credentials not found in .env file.")
    
    dhan_context = DhanContext(client_id, access_token)
    dhan = dhanhq(dhan_context)
    return dhan

# src/indian_algo/brokers/dhan_sandbox.py (continued)

def place_sandbox_order(dhan, security_id, exchange_segment, transaction_type, quantity, order_type, price):
    """Place a sandbox order. Defaults to LIMIT to avoid slippage in testing."""
    order_id = dhan.place_order(
        security_id=str(security_id),
        exchange_segment=exchange_segment,
        transaction_type=transaction_type,
        quantity=int(quantity),
        order_type=order_type,
        product_type="INTRADAY",
        price=float(price) if order_type == "LIMIT" else 0
    )
    return order_id
