#!/usr/bin/env python3
"""Debug Alpaca API authentication."""

import os
from dotenv import load_dotenv
import requests

load_dotenv()

api_key = os.getenv('ALPACA_API_KEY')
api_secret = os.getenv('ALPACA_API_SECRET')

print("\n" + "="*80)
print("ALPACA API DEBUG")
print("="*80)
print(f"\nAPI Key (first 20 chars): {api_key[:20] if api_key else 'NOT SET'}")
print(f"API Secret (first 20 chars): {api_secret[:20] if api_secret else 'NOT SET'}")

# Test 1: Headers format
headers = {
    'APCA-API-KEY-ID': api_key,
    'APCA-API-SECRET-KEY': api_secret,
    'Content-Type': 'application/json'
}

print(f"\nHeaders being sent:")
for k, v in headers.items():
    if v:
        print(f"  {k}: {v[:30]}...")
    else:
        print(f"  {k}: EMPTY")

# Test 2: Make request
url = "https://paper-api.alpaca.markets/v2/account"
print(f"\nMaking request to: {url}")

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*80 + "\n")
