"""
# ============================================================================
# MAIN ENTRY POINT - TRADING SYSTEM
# ============================================================================
# Production-ready trading system with automated scanning and execution
# ============================================================================
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from datetime import datetime, timedelta
from src.config import SystemConfig
from src.scanner import TradingScanner
from src.trading import PaperTradingAccount, AlpacaBroker, RiskManager, SignalFilter, TradeLogger


def _is_kill_switch_triggered(config: SystemConfig) -> bool:
    """Return True if emergency stop is enabled and currently triggered."""
    if not config.get('kill_switch_enabled', True):
        return False
    return bool(config.get('kill_switch_triggered', False))


def main_auto_trade() -> None:
    """Run automated trading mode - execute real trades based on signals."""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + f"{'🤖 AUTO-TRADING MODE - EXECUTING TRADES':^78}" + "█")
    print("█" + " "*78 + "█")
    print("█"*80 + "\n")
    
    try:
        # Initialize systems
        config = SystemConfig()
        config.print_summary()

        max_hold_days = int(config.get('max_hold_days', 7))

        if _is_kill_switch_triggered(config):
            print("\n🛑 KILL SWITCH ACTIVE - no orders will be submitted.\n")
            return

        print("\nSAFETY POLICY:")
        print(f"  Max Hold Window: {max_hold_days} day(s)")
        print("  Kill Switch: ENABLED")
        
        print("\n" + "="*80)
        print("INITIALIZING BROKER CONNECTION...")
        print("="*80 + "\n")
        
        # Connect to Alpaca
        broker = AlpacaBroker(
            api_key=os.getenv('ALPACA_API_KEY'),
            api_secret=os.getenv('ALPACA_API_SECRET'),
            paper_trading=config.get('paper_trading', True)
        )
        
        if not broker.connected:
            print("❌ Failed to connect to Alpaca!\n")
            return
        
        # Get account info
        print("\nACCOUNT STATUS:")
        print(f"  Balance: ${broker.get_balance():,.2f}")
        print(f"  Positions: {len(broker.get_positions())}")
        
        # Initialize trading components
        scanner = TradingScanner()
        risk_manager = RiskManager(
            account_size=config.get('account_size', 300),
            max_positions=config.get('max_positions', 3)
        )
        signal_filter = SignalFilter(min_score=0.0)
        trade_logger = TradeLogger()
        
        print("\n" + "="*80)
        print("SCANNING MARKET FOR SIGNALS...")
        print("="*80 + "\n")
        
        # Scan for signals
        signals = scanner.scan(period='1y')
        print(f"\n✓ Generated {len(signals)} total signals\n")
        
        # Filter signals
        filtered_signals = signal_filter.filter_signals(signals)
        print(f"✓ {len(filtered_signals)} signals passed quality filter\n")
        
        # Get current positions
        positions = broker.get_positions()
        position_count = len(positions)
        max_pos = config.get('max_positions', 3)
        
        print("="*80)
        print("EXECUTION PLAN")
        print("="*80)
        print(f"Current Positions: {position_count}/{max_pos}")
        print(f"Available Slots: {max_pos - position_count}\n")
        
        trades_executed = 0
        
        # Execute BUY signals
        for signal in filtered_signals:
            if _is_kill_switch_triggered(config):
                print("🛑 Kill switch triggered during execution. Stopping new orders.\n")
                break

            if position_count >= max_pos:
                print(f"⚠️  Position limit reached. Stopping execution.\n")
                break
            
            ticker = signal.get('ticker')
            signal_type = signal.get('signal')
            price = signal.get('price', 0)
            score = signal.get('score', 0)
            
            if ticker and signal_type == 'BUY' and price > 0:
                # Calculate position size
                shares = risk_manager.calculate_position_size(price)
                profit_target = risk_manager.calculate_sell_target(price)
                exit_deadline = datetime.utcnow() + timedelta(days=max_hold_days)
                
                print(f"📊 EXECUTING: {ticker}")
                print(f"   Signal: {signal_type} | Score: {score:.2f}")
                print(f"   Price: ${price:.2f}")
                print(f"   Shares: {int(shares)}")
                print(f"   Profit Target: ${profit_target:.2f}")
                print(f"   Max Hold Until: {exit_deadline.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                
                # Place order
                try:
                    order = broker.place_buy_order(
                        symbol=ticker,
                        shares=int(shares),
                        limit_price=None
                    )
                    
                    if order and order.get('success', False):
                        print(f"   ✅ ORDER PLACED\n")
                        
                        # Log trade
                        trade_logger.log_trade({
                            'symbol': ticker,
                            'side': 'BUY',
                            'shares': int(shares),
                            'price': price
                        })
                        
                        trades_executed += 1
                        position_count += 1
                    else:
                        print(f"   ❌ ORDER FAILED\n")
                        
                except Exception as e:
                    print(f"   ❌ ERROR: {e}\n")
        
        # Summary
        print("\n" + "="*80)
        print("EXECUTION COMPLETE")
        print("="*80)
        print(f"Trades Executed: {trades_executed}")
        print(f"Final Balance: ${broker.get_balance():,.2f}")
        print(f"Final Positions: {len(broker.get_positions())}")
        print("\nCheck trade_logs/ for detailed execution log.\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")


def main_scan_only() -> None:
    """Run scanner in analysis-only mode (no trading)."""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + f"{'TRADING SCANNER - ANALYSIS ONLY MODE':^78}" + "█")
    print("█" + " "*78 + "█")
    print("█"*80 + "\n")
    
    try:
        # Initialize
        config = SystemConfig()
        config.print_summary()
        
        # Run scanner
        scanner = TradingScanner()
        signals = scanner.scan(period='1y')
        
        # Display results
        scanner.print_results(top_n=15)
        
        if signals:
            print(f"\n✓ {len(signals)} signals generated")
            for sig in signals[:5]:
                print(f"  - {sig['ticker']}: {sig.get('signal', 'HOLD')} @ ${sig['price']:.2f}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def main_paper_trading() -> None:
    """Run paper trading mode for testing."""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + f"{'PAPER TRADING SESSION':^78}" + "█")
    print("█" + " "*78 + "█")
    print("█"*80 + "\n")
    
    try:
        # Initialize systems
        config = SystemConfig()
        scanner = TradingScanner()
        paper_account = PaperTradingAccount(starting_balance=300.0)
        risk_manager = RiskManager(account_size=300, max_positions=3)
        signal_filter = SignalFilter(min_score=0.0)
        
        print("Systems initialized:")
        print("  ✓ Scanner ready")
        print("  ✓ Paper account ready ($300)")
        print("  ✓ Risk management active")
        print()
        
        # Scan market
        signals = scanner.scan(period='1y')
        scanner.print_results(top_n=10)
        
        # Filter signals
        filtered = signal_filter.filter_signals(signals)
        print(f"\n✓ {len(filtered)} quality signals after filtering\n")
        
        # Paper account summary
        paper_account.print_summary()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == 'paper':
            main_paper_trading()
        elif mode == 'auto' or mode == 'trade':
            main_auto_trade()
        else:
            main_scan_only()
    else:
        # Check config for auto_trade setting
        config = SystemConfig()
        if config.get('auto_trade'):
            main_auto_trade()
        else:
            main_scan_only()
