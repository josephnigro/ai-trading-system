#!/usr/bin/env python3
"""Test Alpaca API authentication and connection."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from src.trading import AlpacaBroker

print("\n" + "="*80)
print("ALPACA API CONNECTION TEST")
print("="*80 + "\n")

# Check for credentials
api_key = os.getenv('ALPACA_API_KEY')
api_secret = os.getenv('ALPACA_API_SECRET')

print("[1/3] Checking credentials...")
if not api_key:
    print("  ✗ ALPACA_API_KEY not set in .env")
    sys.exit(1)
if not api_secret:
    print("  ✗ ALPACA_API_SECRET not set in .env")
    sys.exit(1)
print("  ✓ Credentials found in .env")

# Test connection
print("\n[2/3] Testing paper trading connection...")
try:
    broker = AlpacaBroker(
        api_key=api_key,
        api_secret=api_secret,
        paper_trading=True  # Paper trading for testing
    )
    
    if broker.connected:
        print("  ✓ Connected to Alpaca (PAPER)")
    else:
        print("  ✗ Connection failed - check API credentials")
        sys.exit(1)
        
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Get account info
print("\n[3/3] Retrieving account information...")
try:
    balance = broker.get_balance()
    positions = broker.get_positions()
    
    print(f"  ✓ Account Balance: ${balance:,.2f}")
    print(f"  ✓ Open Positions: {len(positions)}")
    
except Exception as e:
    print(f"  ✗ Error getting account info: {e}")
    sys.exit(1)

print("\n" + "="*80)
print("✓ ALPACA CONNECTION SUCCESSFUL")
print("="*80 + "\n")
print("Next steps:")
print("  1. Set up trading parameters in src/config/system_config.py")
print("  2. Run: python main.py paper  (for paper trading)")
print("  3. Review trades in trade_logs/\n")
