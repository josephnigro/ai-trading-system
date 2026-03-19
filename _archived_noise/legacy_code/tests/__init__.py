"""Unified test suite for the trading system."""

from core.scanner import Scanner


class SystemTests:
    """Run comprehensive system tests."""
    
    @staticmethod
    def test_data_engine():
        """Test data fetching."""
        print("\n" + "="*60)
        print("TEST: Data Engine")
        print("="*60)
        
        tickers = ['AAPL', 'MSFT']
        scanner = Scanner(tickers)
        
        from core import DataEngine
        engine = DataEngine(tickers)
        data = engine.fetch_data(period="3mo")
        
        assert len(data) > 0, "No data fetched"
        print("✓ Data engine working")
        return True
    
    @staticmethod
    def test_scanner_ai_mode():
        """Test AI mode scanner."""
        print("\n" + "="*60)
        print("TEST: Scanner - AI Mode")
        print("="*60)
        
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        scanner = Scanner(tickers)
        results = scanner.scan(period="6mo", mode="ai")
        
        assert len(results) > 0, "No results generated"
        print(f"✓ Generated {len(results)} AI signals")
        return True
    
    @staticmethod
    def test_scanner_momentum_mode():
        """Test momentum mode scanner."""
        print("\n" + "="*60)
        print("TEST: Scanner - Momentum Mode")
        print("="*60)
        
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
        scanner = Scanner(tickers)
        results = scanner.scan(period="1y", mode="momentum")
        
        print(f"✓ Generated {len(results)} momentum signals")
        return True
    
    @staticmethod
    def test_risk_manager():
        """Test risk management."""
        print("\n" + "="*60)
        print("TEST: Risk Manager")
        print("="*60)
        
        from trading.risk_manager import RiskManager
        
        rm = RiskManager(account_size=25000)
        shares, risk, value = rm.calculate_position_size(100, 95)
        
        assert shares > 0, "Position size calculation failed"
        assert risk > 0, "Risk calculation failed"
        print(f"✓ Position calculated: {shares} shares, ${risk:.2f} risk")
        return True
    
    @staticmethod
    def test_paper_trading():
        """Test paper trading."""
        print("\n" + "="*60)
        print("TEST: Paper Trading")
        print("="*60)
        
        from trading.paper_trading import PaperTradingAccount
        
        account = PaperTradingAccount(starting_balance=1000)
        account.buy('TEST', 5, 10, 'Test buy')
        
        assert account.balance < 1000, "Balance not updated"
        assert 'TEST' in account.positions, "Position not recorded"
        print("✓ Paper trading working")
        return True
    
    @staticmethod
    def test_signal_filter():
        """Test signal filtering."""
        print("\n" + "="*60)
        print("TEST: Signal Filter")
        print("="*60)
        
        from trading.signal_filter import SignalFilter
        
        filt = SignalFilter()
        stock_data = {'price': 50.0, 'volume_dollars': 1000000}
        signal = {
            'signal': 'BUY',
            'technical': {'rsi': 45, 'macd_trend': 'BULLISH'},
            'ml_prediction': {'confidence': 0.7},
            'sentiment': {'overall_score': 0.5}
        }
        
        passes, reasons = filt.filter_signal(stock_data, signal)
        assert passes, f"Filter failed: {reasons}"
        print("✓ Signal filter working")
        return True
    
    @staticmethod
    def run_all():
        """Run all tests."""
        print("\n" + "🧪 RUNNING SYSTEM TESTS" + "\n")
        
        tests = [
            SystemTests.test_data_engine,
            SystemTests.test_scanner_ai_mode,
            SystemTests.test_scanner_momentum_mode,
            SystemTests.test_risk_manager,
            SystemTests.test_paper_trading,
            SystemTests.test_signal_filter,
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"✗ Test failed: {e}")
                failed += 1
        
        print("\n" + "="*60)
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("="*60 + "\n")
        
        return failed == 0


if __name__ == "__main__":
    SystemTests.run_all()
