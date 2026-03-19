"""Broker abstraction layer for paper and live trading."""

from datetime import datetime
from .alpaca_broker import AlpacaBroker
from .paper_trading import PaperTradingAccount


class RobinhoodBroker:
    """Interface for Robinhood API (stub implementation)."""
    
    def __init__(self, username=None, password=None, paper_trading=True):
        self.username = username
        self.paper_trading = paper_trading
        self.is_connected = False
        self.rh = None
        
        print("📡 Robinhood Integration Framework")
        print("Note: robinhood library is not officially supported")
        
        if username and password:
            self.connect(username, password)
    
    def connect(self, username, password):
        """Connect to Robinhood API (stub)."""
        try:
            from robin_stocks import robinhood as rh  # type: ignore
            self.rh = rh
            self.is_connected = rh.login(username, password)
            if self.is_connected:
                print("✓ Connected to Robinhood")
            return self.is_connected
        except ImportError:
            print("⚠️  robinhood library not installed")
            return False
    
    def buy(self, symbol, shares):
        """Place a buy order."""
        if self.paper_trading:
            print(f"📋 PAPER: Buy {shares} shares of {symbol}")
            return f"PAPER_BUY_{symbol}_{shares}"
        return None
    
    def sell(self, symbol, shares):
        """Place a sell order."""
        if self.paper_trading:
            print(f"📋 PAPER: Sell {shares} shares of {symbol}")
            return f"PAPER_SELL_{symbol}_{shares}"
        return None
    
    def get_account_value(self):
        """Get account equity."""
        return None
    
    def disconnect(self):
        """Disconnect from Robinhood."""
        self.is_connected = False


class BrokerAbstraction:
    """Abstract interface for paper and live brokers."""
    
    def __init__(self, broker_type='alpaca', **kwargs):
        if broker_type == 'paper':
            self.broker = PaperTradingAccount(kwargs.get('starting_balance', 25000))
        elif broker_type == 'alpaca':
            self.broker = AlpacaBroker(
                paper_trading=kwargs.get('paper_trading', True),
                api_key=kwargs.get('api_key'),
                api_secret=kwargs.get('api_secret')
            )
        elif broker_type == 'robinhood':
            self.broker = RobinhoodBroker(
                username=kwargs.get('username'),
                password=kwargs.get('password'),
                paper_trading=kwargs.get('paper_trading', True)
            )
        else:
            raise ValueError(f"Unknown broker: {broker_type}")
        
        self.broker_type = broker_type
    
    def buy(self, symbol, shares, price=None, reason=''):
        """Buy shares."""
        if self.broker_type == 'paper':
            success = self.broker.buy(symbol, shares, price, reason)  # type: ignore
            if not success:
                return None
            return self._paper_order_id('BUY', symbol)
        elif self.broker_type == 'alpaca':
            order = self.broker.place_buy_order(symbol, shares, limit_price=price)  # type: ignore
            if order.get('success'):
                return order.get('order_id')
            return None
        return self.broker.buy(symbol, shares)  # type: ignore
    
    def sell(self, symbol, shares, price=None, reason=''):
        """Sell shares."""
        if self.broker_type == 'paper':
            success = self.broker.sell(symbol, shares, price, reason)  # type: ignore
            if not success:
                return None
            return self._paper_order_id('SELL', symbol)
        elif self.broker_type == 'alpaca':
            order = self.broker.place_sell_order(symbol, shares, limit_price=price)  # type: ignore
            if order.get('success'):
                return order.get('order_id')
            return None
        return self.broker.sell(symbol, shares)  # type: ignore
    
    def get_account_value(self):
        """Get account balance/equity."""
        if self.broker_type == 'paper':
            return self.broker.balance  # type: ignore
        elif self.broker_type == 'alpaca':
            return self.broker.get_account_balance()  # type: ignore
        return 0.0

    def _paper_order_id(self, side, symbol):
        """Create a synthetic order id for simulated fills."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"PAPER_{side}_{symbol}_{timestamp}"
