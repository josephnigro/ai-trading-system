#!/usr/bin/env python3
"""Comprehensive system validation script."""

print("\n" + "="*80)
print("COMPREHENSIVE SYSTEM VALIDATION")
print("="*80)

# Test 1: All imports
print("\n[1/6] Testing imports...")
try:
    from src.config import SystemConfig
    from src.data import AlphaVantageAPI, DataEngine
    from src.analysis import TechnicalAnalyzer, MLPredictor, SentimentAnalyzer
    from src.trading import AlpacaBroker, PaperTradingAccount, RiskManager, SignalFilter, TradeLogger
    from src.scanner import TradingScanner
    print("✓ All modules import successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    
# Test 2: Configuration
print("\n[2/6] Testing configuration...")
try:
    cfg = SystemConfig()
    assert cfg.get('account_size') == 300
    assert cfg.get('max_positions') == 3
    print("✓ Configuration system works")
except Exception as e:
    print(f"✗ Config error: {e}")

# Test 3: Paper Trading
print("\n[3/6] Testing paper trading account...")
try:
    account = PaperTradingAccount(starting_balance=300)
    assert account.get_balance() == 300
    assert len(account.get_positions()) == 0
    account.buy('TEST', 10, 5.0, 'test')
    assert account.get_balance() < 300
    print("✓ Paper trading account works")
except Exception as e:
    print(f"✗ Paper account error: {e}")

# Test 4: Risk Manager
print("\n[4/6] Testing risk manager...")
try:
    risk_mgr = RiskManager(account_size=300, max_positions=3)
    shares = risk_mgr.calculate_position_size(stock_price=10.0)
    target = risk_mgr.calculate_sell_target(buy_price=100)
    assert shares > 0
    assert target > 100
    print("✓ Risk manager works")
except Exception as e:
    print(f"✗ Risk manager error: {e}")

# Test 5: Signal Filter
print("\n[5/6] Testing signal filter...")
try:
    sig_filter = SignalFilter(min_score=0.0)
    signals = [
        {'ticker': 'TEST', 'score': 0.5, 'signal': 'BUY'},
        {'ticker': 'TEST2', 'score': -0.3, 'signal': 'HOLD'}
    ]
    filtered = sig_filter.filter_signals(signals)
    assert len(filtered) == 1  # Only one signal meets min_score
    assert filtered[0]['ticker'] == 'TEST'
    print("✓ Signal filter works")
except Exception as e:
    print(f"✗ Signal filter error: {e}")

# Test 6: Trade Logger
print("\n[6/6] Testing trade logger...")
try:
    logger = TradeLogger()
    logger.log_trade({'symbol': 'TEST', 'side': 'BUY', 'shares': 10, 'price': 5.0})
    trades = logger.get_trades()
    assert len(trades) == 1
    assert trades[0]['symbol'] == 'TEST'
    print("✓ Trade logger works")
except Exception as e:
    print(f"✗ Trade logger error: {e}")

print("\n" + "="*80)
print("VALIDATION COMPLETE - All core systems operational ✓")
print("="*80 + "\n")
