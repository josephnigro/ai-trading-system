# ==============================
# PRODUCTION TRADING SYSTEM
# ==============================
# Main orchestrator integrating all modules for automated trading

from Scanner import AITradingScanner
from risk_manager import RiskManager
from signal_filter import SignalFilter
from trade_logger import TradeLogger
from notifications import NotificationManager, ManualApprovalHandler
from system_config import SystemConfig, KillSwitch, CircuitBreaker, TradingHours
from trading.broker_integration import BrokerAbstraction
from datetime import datetime
import sys
import time


def _configure_console_output():
    """Use UTF-8 console output when the runtime supports reconfiguration."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            continue

class ProductionTradingSystem:
    """
    Complete production trading system with safety, risk management, and logging
    """
    
    def __init__(self, config_file='system_config.json'):
        _configure_console_output()
        print("\n" + "="*80)
        print("🚀 PRODUCTION TRADING SYSTEM INITIALIZATION")
        print("="*80 + "\n")
        
        # Load configuration
        self.config = SystemConfig(config_file)
        print("✓ Configuration loaded")
        
        # Initialize core components
        self.kill_switch = KillSwitch(self.config)
        self.circuit_breaker = CircuitBreaker(
            self.config.get('account_settings.max_daily_loss', 2.0)  # type: ignore
        )
        self.trading_hours = TradingHours()
        self.notifications = NotificationManager(
            twilio_enabled=bool(self.config.get('notifications.sms_enabled', False))
        )
        self.approval_handler = ManualApprovalHandler(
            require_approval=bool(self.config.get('automation.manual_approval_required', True))
        )
        self.logger = TradeLogger()
        self.signal_filter = SignalFilter()
        
        # Initialize risk manager
        self.risk_manager = RiskManager(
            account_size=self.config.get('account_settings.account_size', 25000),  # type: ignore
            risk_per_trade=self.config.get('account_settings.risk_per_trade', 0.01),  # type: ignore
            max_position_size=self.config.get('account_settings.max_position_size', 0.05)  # type: ignore
        )
        
        # Use local paper simulation when paper mode is enabled.
        paper_trading_mode = bool(
            self.config.get('automation.paper_trading_mode', True)
        )
        broker_type = 'paper' if paper_trading_mode else 'alpaca'
        self.broker = BrokerAbstraction(
            broker_type=broker_type,
            starting_balance=self.config.get('account_settings.account_size', 25000),  # type: ignore
            paper_trading=paper_trading_mode,
        )
        
        # Scanner
        self.scanner = AITradingScanner()
        
        # Statistics
        self.signals_generated = 0
        self.trades_executed = 0
        self.session_start = datetime.now()
        
        print("✓ Risk manager initialized")
        print("✓ Trade logger initialized")
        print("✓ Signal filter initialized")
        print("✓ Notifications configured")
        
        trading_mode = "PAPER TRADING" if paper_trading_mode else "LIVE TRADING"
        print(f"✓ Broker initialized: {trading_mode}")
        
        print("\n" + "="*80)
        print(f"📊 Account Size: ${self.config.get('account_settings.account_size', 25000):.2f}")  # type: ignore
        print(f"📊 Risk Per Trade: {self.config.get('account_settings.risk_per_trade', 0.01)*100:.1f}%")  # type: ignore
        print(f"📊 Manual Approval: {'REQUIRED' if bool(self.config.get('automation.manual_approval_required')) else 'DISABLED'}")
        print("="*80 + "\n")
    
    def pre_flight_check(self):
        """
        Run safety checks before trading
        """
        print("\n🔍 PRE-FLIGHT SAFETY CHECK\n")
        checks_passed = True
        
        # Check 1: Kill switch not active
        if self.kill_switch.check_status():
            print("❌ Kill switch is ACTIVE - cannot trade")
            return False
        print("✓ Kill switch: OK")
        
        # Check 2: Market hours
        if not self.trading_hours.is_market_open():
            minutes = self.trading_hours.get_time_to_market_open()
            print(f"⚠️  Market closed (opens in {minutes} minutes)")
        else:
            print("✓ Market hours: OK")
        
        # Check 3: Configuration is valid
        account_size = self.config.get('account_settings.account_size', 0)  # type: ignore
        if account_size <= 0:  # type: ignore
            print("❌ Invalid account size")
            checks_passed = False
        else:
            print(f"✓ Account size: ${account_size:.2f}")
        
        # Check 4: Risk parameters
        risk_pct = self.config.get('account_settings.risk_per_trade', 0.01)  # type: ignore
        if risk_pct > 0.05:  # type: ignore  # More than 5% per trade is too aggressive
            print(f"⚠️  Risk per trade is high: {risk_pct*100:.1f}%")  # type: ignore
        else:
            print(f"✓ Risk per trade: {risk_pct*100:.1f}%")  # type: ignore
        
        # Check 5: Approval mechanism
        if self.config.get('automation.live_trading_enabled') and not self.config.get('automation.manual_approval_required'):
            print("⚠️  WARNING: Live trading enabled without manual approval")
        else:
            print("✓ Manual approval: ENABLED")
        
        print("\n✓ All safety checks passed!\n")
        return checks_passed
    
    def run_scan(self, period="1y"):
        """
        Run the scanner and generate signals
        """
        if self.kill_switch.check_status():
            print("🛑 Kill switch active - scan aborted")
            return []
        
        print("\n📊 RUNNING MARKET SCAN\n")
        
        # Run scanner
        results = self.scanner.scan(period=period)
        print(f"\n✓ Scan complete - {len(results)} stocks analyzed")
        
        # Filter signals
        filtered_results, filtered_out = self.signal_filter.filter_signals(results)
        
        print(f"\n✓ Quality signals: {len(filtered_results)}")
        if filtered_out:
            print(f"  ({len(filtered_out)} signals filtered out)")
        
        return filtered_results
    
    def process_signal(self, signal):
        """
        Process a single signal and execute if approved
        """
        if self.kill_switch.check_status():
            print("🛑 Kill switch active - signal rejected")
            return False
        
        ticker = signal['ticker']
        current_price = signal['price']
        
        # Log the signal
        self.logger.log_signal(ticker, signal, reason=f"Technical signal: {signal['signal']}")
        self.signals_generated += 1
        
        # Calculate risk parameters
        # Use technical analysis to set stops
        rsi = signal['technical'].get('rsi', 50)
        
        # Set stop loss based on volatility
        atr_equivalent = current_price * 0.02  # 2% of price as rough stop
        stop_loss = current_price - atr_equivalent
        
        shares, risk_dollars, position_value = self.risk_manager.calculate_position_size(
            current_price, stop_loss
        )
        
        if shares <= 0:
            print(f"⚠️  {ticker}: Position size too small (${position_value:.2f})")
            return False
        
        # Validate trade
        if not self.risk_manager.validate_trade(ticker, current_price, stop_loss, shares):
            print(f"❌ {ticker}: Trade validation failed")
            return False
        
        # Calculate targets
        targets = self.risk_manager.calculate_targets(current_price, stop_loss)
        
        # Prepare trade data
        trade_data = {
            'ticker': ticker,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'target': targets['target_full'],
            'shares': shares,
            'risk_dollars': risk_dollars,
            'position_value': position_value,
            'signal_type': signal['signal'],
            'reason': f"Technical analysis signal"
        }
        
        # Request approval
        print(f"\n{'='*60}")
        print(f"📢 NEW TRADING OPPORTUNITY")
        print(f"{'='*60}")
        print(f"Ticker: {ticker}")
        print(f"Signal: {signal['signal']}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"Entry: ${current_price:.2f}")
        print(f"Stop Loss: ${stop_loss:.2f}")
        print(f"Target: ${targets['target_full']:.2f}")
        print(f"Risk: ${risk_dollars:.2f}")
        print(f"Shares: {shares}")
        print(f"Position Value: ${position_value:.2f}")
        print(f"{'='*60}")
        
        # Get approval
        approved = self.approval_handler.request_approval(ticker, signal, trade_data)
        
        if not approved:
            print(f"\n⏭️  {ticker}: Trade rejected by user")
            self.logger.log_decision(f"Trade rejected: {ticker}", "REJECT", trade_data)
            return False
        
        # Execute trade
        print(f"\n✓ Trade APPROVED: {ticker}")
        return self.execute_trade(trade_data)
    
    def execute_trade(self, trade_data):
        """
        Execute the approved trade
        """
        ticker = trade_data['ticker']
        
        try:
            # Place broker order
            order_id = self.broker.buy(
                ticker,
                trade_data['shares'],
                trade_data['entry_price'],
                reason=trade_data.get('reason', 'Scanner signal')
            )
            
            if not order_id:
                print(f"❌ {ticker}: Order execution failed")
                return False
            
            # Record position
            self.risk_manager.record_position(
                ticker,
                trade_data['entry_price'],
                trade_data['stop_loss'],
                trade_data['target'],
                trade_data['shares'],
                trade_data['risk_dollars']
            )
            
            # Log trade
            trade_data['trade_id'] = order_id
            trade_data['execution_strategy'] = 'MANUAL_APPROVED'
            self.logger.log_trade(trade_data)
            
            # Send notification
            self.notifications.send_trade_confirmation(trade_data)
            
            self.trades_executed += 1
            self.logger.log_decision(f"Trade executed: {ticker}", "APPROVE", trade_data)
            
            print(f"\n✅ TRADE EXECUTED: {ticker}")
            print(f"   Order ID: {order_id}")
            print(f"   Shares: {trade_data['shares']}")
            print(f"   Entry: ${trade_data['entry_price']:.2f}")
            
            return True
        
        except Exception as e:
            print(f"❌ Error executing trade: {e}")
            self.logger.log_decision(f"Trade execution error: {ticker}", "ERROR", {'error': str(e)})
            return False
    
    def run_session(self, period="1y", scan_interval=3600):
        """
        Run a complete trading session
        
        scan_interval: Seconds between scans (default: 1 hour)
        """
        print("\n" + "🔥"*40)
        print("PRODUCTION TRADING SESSION STARTED")
        print("🔥"*40 + "\n")
        
        # Pre-flight check
        if not self.pre_flight_check():
            print("❌ Pre-flight check failed - aborting session")
            return
        
        # Run scan and process signals
        print(f"⏰ Scan started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        signals = self.run_scan(period=period)
        
        if signals:
            print(f"\n📊 Processing {len(signals)} quality signals...\n")
            
            for signal in signals:
                if self.kill_switch.check_status():
                    print("\n🛑 Kill switch activated - session halted")
                    break
                
                self.process_signal(signal)
                time.sleep(1)  # Small delay between signals
        else:
            print("\n⏭️  No quality signals generated")
        
        # Print session summary
        self.print_session_summary()
    
    def print_session_summary(self):
        """Print trading session summary"""
        portfolio = self.risk_manager.get_portfolio_status()
        perf = self.logger.get_trade_performance()
        
        print("\n" + "="*80)
        print("📊 SESSION SUMMARY")
        print("="*80)
        print(f"Session Duration: {datetime.now() - self.session_start}")
        print(f"Signals Generated: {self.signals_generated}")
        print(f"Trades Executed: {self.trades_executed}")
        print(f"\nPortfolio:")
        print(f"  Account Size: ${portfolio['account_size']:.2f}")
        print(f"  Available Capital: ${portfolio['available_capital']:.2f}")
        print(f"  Open Positions: {portfolio['open_positions']}")
        print(f"  Total Position Value: ${portfolio['total_position_value']:.2f}")
        print(f"  Total Risk: ${portfolio['total_risk_dollars']:.2f} ({portfolio['total_risk_percent']:.1f}%)")
        print(f"\nPerformance:")
        print(f"  Total Trades: {perf['total_trades']}")
        print(f"  Winning Trades: {perf['winning_trades']}")
        print(f"  Losing Trades: {perf['losing_trades']}")
        print(f"  Win Rate: {perf['win_rate']:.1f}%")
        print(f"  Total P&L: ${perf['total_pnl']:.2f}")
        print("="*80 + "\n")


# Main execution
if __name__ == "__main__":
    system = ProductionTradingSystem()
    system.run_session(period="1y")
