#!/usr/bin/env python3
"""
AUTOMATED TRADING SESSION
Run this script to start an unattended automated trading/scanning session.
It will run for a specified duration, collecting data and executing trades.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import time
import sys
from datetime import datetime, timedelta
from production_system import ProductionTradingSystem
from system_config import KillSwitch

def print_header(text):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(f"🤖 {text}")
    print("="*80 + "\n")

def run_automated_session(duration_hours=2, scan_interval_minutes=5, auto_trade=False):
    """
    Run automated trading session unattended.
    
    duration_hours: How long to run (e.g., 2 = 2 hours)
    scan_interval_minutes: How often to scan (e.g., 5 = every 5 minutes)
    auto_trade: If True, execute trades automatically. If False, signals only.
    """
    try:
        print_header("AUTOMATED TRADING SESSION STARTED")
        
        print(f"📋 Configuration:")
        print(f"   Duration: {duration_hours} hours")
        print(f"   Scan Interval: {scan_interval_minutes} minutes")
        print(f"   Auto Trade: {'ENABLED' if auto_trade else 'DISABLED (signals only)'}")
        print(f"   Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize system
        print("\n🚀 Initializing trading system...")
        system = ProductionTradingSystem()
        
        # Pre-flight checks
        print("\n🔍 Running pre-flight safety checks...")
        if not system.pre_flight_check():
            print("\n❌ Safety checks FAILED - aborting")
            sys.exit(1)
        
        print("\n✓ All safety checks passed!")
        
        # Calculate end time
        end_time = datetime.now() + timedelta(hours=duration_hours)
        scan_count = 0
        error_count = 0
        signal_count = 0
        trade_count = 0
        
        print_header(f"AUTOMATED SESSION RUNNING")
        print(f"Will run until: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Main loop
        while datetime.now() < end_time:
            try:
                # Check kill switch
                if system.kill_switch.check_status():
                    print("\n🛑 KILL SWITCH ACTIVATED - STOPPING")
                    break
                
                # Scan the market
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📊 Scanning market...")
                signals = system.run_scan(period="1mo")
                scan_count += 1
                signal_count += len(signals)
                
                if signals:
                    print(f"   Found {len(signals)} quality signals")
                    
                    if auto_trade:
                        # Auto-execute trades
                        for signal in signals[:3]:  # Limit to 3 trades per scan
                            try:
                                success = system.process_signal(signal)
                                if success:
                                    trade_count += 1
                            except Exception as e:
                                print(f"   ⚠️  Error processing signal: {e}")
                                error_count += 1
                    else:
                        # Just collect signals
                        for signal in signals[:5]:
                            print(f"   • {signal['ticker']}: {signal['signal']} @ ${signal['price']:.2f}")
                else:
                    print(f"   No quality signals found")
                
                # Show account status
                try:
                    balance = system.broker.get_account_value()
                    print(f"   💰 Account Balance: ${balance:.2f}")
                except:
                    pass
                
                # Wait for next scan
                time_remaining = end_time - datetime.now()
                if time_remaining.total_seconds() > 0:
                    print(f"\n⏳ Next scan in {scan_interval_minutes} minutes (Ctrl+C to stop)")
                    print(f"   Session ends at: {end_time.strftime('%H:%M:%S')}\n")
                    time.sleep(scan_interval_minutes * 60)
                else:
                    break
            
            except KeyboardInterrupt:
                print("\n\n⏹️  User stopped session (Ctrl+C)")
                break
            except Exception as e:
                error_count += 1
                print(f"   ❌ Error during scan: {e}")
                print(f"   Retrying in {scan_interval_minutes} minutes...\n")
                time.sleep(scan_interval_minutes * 60)
        
        # Summary
        print_header("SESSION COMPLETE")
        print(f"📊 Session Summary:")
        print(f"   Total Scans: {scan_count}")
        print(f"   Signals Found: {signal_count}")
        print(f"   Trades Executed: {trade_count}" if auto_trade else f"   Signals Collected: {signal_count}")
        print(f"   Errors: {error_count}")
        print(f"\n   Session Duration: {(datetime.now() - (end_time - timedelta(hours=duration_hours))).total_seconds() / 60:.1f} minutes")
        
        try:
            balance = system.broker.get_account_value()
            print(f"   Final Balance: ${balance:.2f}")
        except:
            pass
        
        print(f"\n✓ Automated session finished successfully")
        print(f"   Check trade logs: trade_logs/ directory")
        print(f"   Results: scanner_results.csv\n")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Session interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # CONFIGURE THESE SETTINGS
    DURATION_HOURS = 0.5        # How long to run (test first!)
    SCAN_INTERVAL_MINUTES = 2   # Quick scans to find signals
    AUTO_TRADE = False          # Start with False (signals only), set True to auto-trade
    
    print("\n" + "="*80)
    print("⚙️  AUTOMATED TRADING SESSION CONFIGURATOR")
    print("="*80)
    print(f"\nCurrent settings:")
    print(f"  • Duration: {DURATION_HOURS} hours")
    print(f"  • Scan every: {SCAN_INTERVAL_MINUTES} minutes")
    print(f"  • Auto-trading: {'ON' if AUTO_TRADE else 'OFF (signals only)'}")
    print(f"\nEdit this script to change settings before running.")
    print(f"\nStarting in 5 seconds... (Press Ctrl+C to cancel)\n")
    
    time.sleep(5)
    
    # Run the session
    run_automated_session(
        duration_hours=int(DURATION_HOURS),
        scan_interval_minutes=SCAN_INTERVAL_MINUTES,
        auto_trade=AUTO_TRADE
    )
