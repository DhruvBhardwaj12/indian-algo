"""Test Script for Dhan Sandbox via Direct REST API."""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def get_headers():
    client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
    access_token = os.getenv("DHAN_SANDBOX_ACCESS_TOKEN", "").strip()
    
    if not client_id or not access_token:
        raise ValueError("Dhan credentials not found in .env file.")
        
    return {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def place_sandbox_order():
    print("Placing dummy LIMIT BUY order via direct REST API...")
    headers = get_headers()
    
    # The payload for an intraday limit order
    payload = {
        "dhanClientId": headers["client-id"],
        "transactionType": "BUY",
        "exchangeSegment": "NSE_FNO",
        "productType": "INTRADAY",
        "orderType": "LIMIT",
        "validity": "DAY",
        "securityId": "12345", # Placeholder security ID
        "quantity": 75,
        "price": 100.0,
        "afterMarketOrder": False
    }
    
    url = "https://sandbox.dhan.co/v2/orders"
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"HTTP Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("[SUCCESS] Order request accepted by sandbox.")
        else:
            print("[FAILED] Check the error message above.")
            
    except Exception as e:
        print(f"Request failed: {e}")

def activate_kill_switch():
    print("\nActivating kill switch via direct REST API...")
    headers = get_headers()
    url = "https://sandbox.dhan.co/v2/killswitch?killSwitchStatus=ACTIVATE"
    
    try:
        response = requests.post(url, headers=headers, timeout=10)
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Kill switch failed: {e}")

if __name__ == "__main__":
    place_sandbox_order()
    activate_kill_switch()
    