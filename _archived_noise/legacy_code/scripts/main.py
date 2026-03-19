"""Main entry point for the trading system."""

from core.scanner import Scanner
from trading.signal_filter import SignalFilter
from trading.risk_manager import RiskManager
from trading.paper_trading import PaperTradingAccount
from trading.trade_logger import TradeLogger
from utils.system_config import SystemConfig, KillSwitch, CircuitBreaker, TradingHours
from utils.notifications import NotificationManager, ManualApprovalHandler
from datetime import datetime


class TradingSystem:
    """Main trading system orchestrator."""
    
    def __init__(self, config_file='system_config.json'):
        self.config = SystemConfig(config_file)
        self.kill_switch = KillSwitch(self.config)
        self.circuit_breaker = CircuitBreaker(self.config.get('account_settings.max_daily_loss', 2.0))  # type: ignore
        self.trading_hours = TradingHours()
        self.notifications = NotificationManager()
        self.approval_handler = ManualApprovalHandler(True)
        self.logger = TradeLogger()
        self.signal_filter = SignalFilter()
        self.risk_manager = RiskManager(
            account_size=self.config.get('account_settings.account_size', 25000),  # type: ignore
            risk_per_trade=self.config.get('account_settings.risk_per_trade', 0.01),  # type: ignore
            max_position_size=self.config.get('account_settings.max_position_size', 0.05)  # type: ignore
        )
        self.account = PaperTradingAccount(
            starting_balance=self.config.get('account_settings.account_size', 25000)  # type: ignore
        )
        self.scanner = None
    
    def pre_flight_check(self):
        """Run safety checks before trading."""
        print("\n" + "="*60)
        print("PRE-FLIGHT SAFETY CHECKS")
        print("="*60 + "\n")
        
        checks = []
        
        if self.kill_switch.check_status():
            print("❌ Kill switch is ACTIVE - cannot trade")
            return False
        else:
            print("✓ Kill switch: OFF")
            checks.append(True)
        
        if not self.config.get('automation.paper_trading_mode', True):
            print("⚠️  LIVE TRADING MODE - HIGH RISK!")
        else:
            print("✓ Paper trading: ON (safe mode)")
            checks.append(True)
        
        account_size = self.config.get('account_settings.account_size', 25000)
        if account_size < 5000:  # type: ignore
            print(f"⚠️  Account very small: ${account_size}")
        else:
            print(f"✓ Account size: ${account_size:,.0f}")
            checks.append(True)
        
        if self.config.get('automation.manual_approval_required', True):
            print("✓ Manual approval: REQUIRED (trades need approval)")
            checks.append(True)
        else:
            print("⚠️  Auto-trading enabled (no manual approval)")
        
        return all(checks)
    
    def run_scan(self, period="1y", mode="ai"):
        """Run scanner."""
        if self.kill_switch.check_status():
            print("🛑 Kill switch active - scan aborted")
            return []
        
        print("\n📊 RUNNING SCAN\n")
        
        tickers = Scanner().tickers
        self.scanner = Scanner(tickers)
        results = self.scanner.scan(period=period, mode=mode)
        
        filtered_results, filtered_out = self.signal_filter.filter_signals(results)
        
        print(f"\n✓ Scan complete: {len(filtered_results)} quality signals")
        
        return filtered_results
    
    def run_trading_session(self, period="1y", mode="ai"):
        """Run full trading session."""
        print("\n" + "="*80)
        print("🚀 TRADING SYSTEM - SESSION START")
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        if not self.pre_flight_check():
            print("\n❌ Pre-flight check failed")
            return
        
        signals = self.run_scan(period=period, mode=mode)
        
        if not signals:
            print("\nℹ️  No quality signals generated")
            return
        
        print(f"\n📊 Generated {len(signals)} quality signals")
        print("\n" + "="*80 + "\n")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("AI TRADING SCANNER - MAIN MENU")
    print("="*80 + "\n")
    
    print("1. Run Full Trading Session (AI Mode)")
    print("2. Run Scanner (Momentum Mode)")
    print("3. Test System")
    print("4. View Configuration")
    print("5. Exit\n")
    
    choice = input("Select option (1-5): ").strip()
    
    system = TradingSystem()
    
    if choice == "1":
        system.run_trading_session(mode="ai")
    elif choice == "2":
        system.run_trading_session(mode="momentum")
    elif choice == "3":
        from tests import SystemTests
        SystemTests.run_all()
    elif choice == "4":
        system.config.print_summary()
    elif choice == "5":
        print("\nExiting...")
    else:
        print("\nInvalid choice")


if __name__ == "__main__":
    main()
