# ==============================
# ROBINHOOD BROKER INTEGRATION
# ==============================
# Framework for connecting to Robinhood API for live trading

class RobinhoodBroker:
    """
    Interface for Robinhood API
    Handles order execution and account management
    
    NOTE: Requires robinhood-python library and valid login
    """
    
    def __init__(self, username=None, password=None, use_mfa=True, paper_trading=True):
        """
        Initialize Robinhood connection
        
        username: Robinhood username/email
        password: Robinhood password
        use_mfa: If True, will require 2FA verification
        paper_trading: If True, uses paper (simulation) account
        """
        self.username = username
        self.paper_trading = paper_trading
        self.is_connected = False
        self.rh = None
        self.account_info = None
        
        print("📡 Robinhood Integration Framework")
        print("="*60)
        print("Note: robinhood library is not officially supported by Robinhood")
        print("Use at your own risk and verify orders on your account")
        print("="*60)
        
        if username and password:
            self.connect(username, password, use_mfa)
    
    def connect(self, username, password, use_mfa=True):
        """
        Connect to Robinhood API
        """
        try:
            from robin_stocks import robinhood as rh  # type: ignore
            self.rh = rh
            
            # Login
            print(f"\n🔐 Authenticating with Robinhood...")
            
            login_result = rh.login(username, password, mfa_code=use_mfa)  # type: ignore
            
            if login_result:
                self.is_connected = True
                self.account_info = rh.account.get_account()  # type: ignore
                print(f"✓ Connected to Robinhood")
                print(f"  Account: {self.account_info['username']}")
                return True
            else:
                print(f"✗ Failed to authenticate")
                return False
        
        except ImportError:
            print("⚠️  robinhood library not installed")
            print("Install with: pip install robin_stocks")
            return False
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False
    
    def buy(self, symbol, shares, order_type='market'):
        """
        Place a buy order
        
        symbol: Stock ticker (e.g., 'AAPL')
        shares: Number of shares to buy
        order_type: 'market' or 'limit'
        
        Returns: Order ID if successful
        """
        if not self.is_connected:
            print("❌ Not connected to Robinhood")
            return None
        
        if self.paper_trading:
            print(f"📋 PAPER ORDER: Would buy {shares} shares of {symbol}")
            return f"PAPER_BUY_{symbol}_{shares}"
        
        try:
            print(f"\n📤 Placing BUY order: {shares} shares of {symbol}")
            
            if order_type == 'market':
                result = self.rh.orders.order_buy_market(symbol, shares)  # type: ignore
            else:
                print("Limit orders not implemented yet")
                return None
            
            if result:
                order_id = result['id']
                print(f"✓ Order placed: {order_id}")
                return order_id
            else:
                print(f"✗ Order failed")
                return None
        
        except Exception as e:
            print(f"✗ Error placing order: {e}")
            return None
    
    def sell(self, symbol, shares, order_type='market'):
        """
        Place a sell order
        
        symbol: Stock ticker (e.g., 'AAPL')
        shares: Number of shares to sell
        order_type: 'market' or 'limit'
        
        Returns: Order ID if successful
        """
        if not self.is_connected:
            print("❌ Not connected to Robinhood")
            return None
        
        if self.paper_trading:
            print(f"📋 PAPER ORDER: Would sell {shares} shares of {symbol}")
            return f"PAPER_SELL_{symbol}_{shares}"
        
        try:
            print(f"\n📤 Placing SELL order: {shares} shares of {symbol}")
            
            if order_type == 'market':
                result = self.rh.orders.order_sell_market(symbol, shares)  # type: ignore
            else:
                print("Limit orders not implemented yet")
                return None
            
            if result:
                order_id = result['id']
                print(f"✓ Order placed: {order_id}")
                return order_id
            else:
                print(f"✗ Order failed")
                return None
        
        except Exception as e:
            print(f"✗ Error placing order: {e}")
            return None
    
    def get_account_value(self):
        """Get current account equity"""
        if not self.is_connected:
            return None
        
        try:
            account = self.rh.account.get_account()  # type: ignore
            return float(account['equity'])
        except:
            return None
    
    def get_positions(self):
        """Get all open positions"""
        if not self.is_connected:
            print("❌ Not connected to Robinhood")
            return []
        
        try:
            positions = self.rh.account.get_open_positions()  # type: ignore
            return positions if positions else []
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []
    
    def get_order_status(self, order_id):
        """Check status of an order"""
        if not self.is_connected:
            return None
        
        try:
            order = self.rh.orders.get_order(order_id)  # type: ignore
            return order['state'] if order else None
        except:
            return None
    
    def cancel_order(self, order_id):
        """Cancel a pending order"""
        if not self.is_connected:
            return False
        
        try:
            result = self.rh.orders.cancel_order(order_id)  # type: ignore
            return result is not None
        except:
            return False
    
    def get_quote(self, symbol):
        """Get current quote for a symbol"""
        if not self.is_connected:
            return None
        
        try:
            quote = self.rh.stocks.get_quotes(symbol)[0]  # type: ignore
            return {
                'symbol': symbol,
                'price': float(quote['last_trade_price']),
                'bid': float(quote['bid_price']),
                'ask': float(quote['ask_price']),
                'bid_size': quote['bid_size'],
                'ask_size': quote['ask_size']
            }
        except Exception as e:
            print(f"Error getting quote: {e}")
            return None
    
    def disconnect(self):
        """Disconnect from Robinhood"""
        try:
            self.rh.logout()  # type: ignore
            self.is_connected = False
            print("✓ Disconnected from Robinhood")
        except:
            pass


class BrokerAbstraction:
    """
    Abstract broker interface
    Allows easy switching between paper trading and live brokers
    """
    
    def __init__(self, broker_type='paper', **kwargs):
        """
        broker_type: 'paper' or 'robinhood'
        """
        self.broker_type = broker_type
        self.broker = None
        
        if broker_type == 'paper':
            from paper_trading import PaperTradingAccount
            self.broker = PaperTradingAccount(kwargs.get('starting_balance', 25000))
        elif broker_type == 'robinhood':
            self.broker = RobinhoodBroker(
                username=kwargs.get('username'),
                password=kwargs.get('password'),
                paper_trading=kwargs.get('paper_trading', True)
            )
        else:
            raise ValueError(f"Unknown broker type: {broker_type}")
    
    def buy(self, symbol, shares, price=None, reason=''):
        """Universal buy interface"""
        if self.broker_type == 'paper':
            return self.broker.buy(symbol, shares, price, reason)  # type: ignore
        else:
            return self.broker.buy(symbol, shares)  # type: ignore
    
    def sell(self, symbol, shares, price=None, reason=''):
        """Universal sell interface"""
        if self.broker_type == 'paper':
            return self.broker.sell(symbol, shares, price, reason)  # type: ignore
        else:
            return self.broker.sell(symbol, shares)  # type: ignore
    
    def get_account_value(self):
        """Get account equity/balance"""
        if self.broker_type == 'paper':
            return self.broker.balance  # type: ignore
        else:
            return self.broker.get_account_value()  # type: ignore
    
    def get_positions(self):
        """Get open positions"""
        if self.broker_type == 'paper':
            return self.broker.positions  # type: ignore
        else:
            return self.broker.get_positions()  # type: ignore
