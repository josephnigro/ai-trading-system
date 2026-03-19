# ==============================
# ALPACA BROKER INTEGRATION
# ==============================
# Direct integration with Alpaca API for paper and live trading

import os
import requests
from datetime import datetime
from typing import Optional, Dict, List

class AlpacaBroker:
    """
    Interface for Alpaca API - Best for penny stock trading
    
    Alpaca provides:
    - FREE API access (no approval needed)
    - Paper trading account with $100k virtual funds
    - Real trading with as little as $1
    - Penny stock support
    - Commission-free trading
    """
    
    def __init__(self, api_key: str | None = None, api_secret: str | None = None, 
                 paper_trading: bool = True, base_url: str | None = None):
        """
        Initialize Alpaca connection
        
        Args:
            api_key: Alpaca API key (gets from environment if not provided)
            api_secret: Alpaca API secret (gets from environment if not provided)
            paper_trading: Use paper trading account (default: True)
            base_url: Override API base URL (optional)
        """
        # Get credentials from environment or parameters
        self.api_key = api_key or os.getenv('ALPACA_API_KEY')
        self.api_secret = api_secret or os.getenv('ALPACA_API_SECRET')
        self.paper_trading = paper_trading
        
        # Alpaca API endpoints
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = 'https://paper-api.alpaca.markets' if paper_trading else 'https://api.alpaca.markets'
        
        self.connected = False
        self.account = None
        self.orders = {}
        
        print("[INFO] Alpaca Broker Integration")
        print(f"Mode: {'Paper Trading' if paper_trading else 'Live Trading'}")
        print("Platform: Alpaca (Commission-free penny stock trading)")
        
        if not self.api_key or not self.api_secret:
            print("[ERR] Missing Alpaca credentials in .env or parameters")
            return
        
        # Test connection
        if self._test_connection():
            self.connected = True
            print("[OK] Connected to Alpaca")
    
    def _test_connection(self) -> bool:
        """Test connection to Alpaca API"""
        try:
            headers = {
                'APCA-API-KEY-ID': self.api_key,
            }
            response = requests.get(f"{self.base_url}/v2/account", headers=headers, timeout=5)
            
            if response.status_code == 200:
                self.account = response.json()
                return True
            else:
                print(f"[ERR] Alpaca connection failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERR] Connection error: {e}")
            return False
    
    def place_buy_order(self, symbol: str, shares: int, limit_price: float | None = None) -> Dict:
        """Place a buy order on Alpaca."""
        if not self.connected:
            print("[ERR] Not connected to Alpaca")
            return {'success': False, 'error': 'Not connected'}
        
        try:
            # Prepare order data
            order_data = {
                'symbol': symbol,
                'qty': shares,
                'side': 'buy',
                'type': 'limit' if limit_price else 'market',
                'time_in_force': 'day'
            }
            
            if limit_price:
                order_data['limit_price'] = limit_price
            
            # Submit order
            headers = {'APCA-API-KEY-ID': self.api_key}
            response = requests.post(
                f"{self.base_url}/v2/orders",
                json=order_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                order = response.json()
                order_id = order['id']
                
                self.orders[order_id] = {
                    'symbol': symbol,
                    'shares': shares,
                    'side': 'buy',
                    'price': limit_price or 'market',
                    'status': 'pending',
                    'timestamp': datetime.now()
                }
                
                print(f"[OK] BUY order placed: {symbol} x{shares} @ ${limit_price if limit_price else 'market'}")
                return {
                    'success': True,
                    'order_id': order_id,
                    'symbol': symbol,
                    'shares': shares
                }
            else:
                error_msg = response.json().get('message', 'Unknown error')
                print(f"[ERR] Order placement failed: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            print(f"[ERR] {e}")
            return {'success': False, 'error': str(e)}
    
    def place_sell_order(self, symbol: str, shares: int, limit_price: Optional[float] = None) -> Dict:
        """Place a sell order on Alpaca."""
        if not self.connected:
            print("[ERR] Not connected to Alpaca")
            return {'success': False, 'error': 'Not connected'}
        
        try:
            # Prepare order data
            order_data = {
                'symbol': symbol,
                'qty': shares,
                'side': 'sell',
                'type': 'limit' if limit_price else 'market',
                'time_in_force': 'day'
            }
            
            if limit_price:
                order_data['limit_price'] = limit_price
            
            # Submit order
            headers = {'APCA-API-KEY-ID': self.api_key}
            response = requests.post(
                f"{self.base_url}/v2/orders",
                json=order_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                order = response.json()
                order_id = order['id']
                
                self.orders[order_id] = {
                    'symbol': symbol,
                    'shares': shares,
                    'side': 'sell',
                    'price': limit_price or 'market',
                    'status': 'pending',
                    'timestamp': datetime.now()
                }
                
                print(f"[OK] SELL order placed: {symbol} x{shares} @ ${limit_price if limit_price else 'market'}")
                return {
                    'success': True,
                    'order_id': order_id,
                    'symbol': symbol,
                    'shares': shares
                }
            else:
                error_msg = response.json().get('message', 'Unknown error')
                print(f"[ERR] Order placement failed: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            print(f"[ERR] {e}")
            return {'success': False, 'error': str(e)}
    
    def get_account_balance(self) -> float:
        """Get current account balance."""
        if not self.account:
            return 0.0
        return float(self.account.get('buying_power', 0))
    
    def get_positions(self) -> Dict:
        """Get current open positions."""
        try:
            headers = {'APCA-API-KEY-ID': self.api_key}
            response = requests.get(f"{self.base_url}/v2/positions", headers=headers, timeout=5)
            
            if response.status_code == 200:
                positions = response.json()
                return {p['symbol']: {
                    'shares': int(p['qty']),
                    'avg_price': float(p['avg_fill_price']),
                    'current_price': float(p['current_price']),
                    'unrealized_pl': float(p['unrealized_pl'])
                } for p in positions}
            return {}
        except Exception as e:
            print(f"[ERR] Failed to get positions: {e}")
            return {}
    
    def get_order_status(self, order_id: str) -> Dict:
        """Get status of a specific order."""
        if order_id not in self.orders:
            return {'status': 'unknown'}
        
        return self.orders[order_id]


class BrokerFactory:
    """
    Universal broker interface - easily switch between Alpaca, Robinhood, etc.
    """
    
    def __init__(self, broker_type='alpaca', paper_trading=True, **kwargs):
        """
        Create broker instance
        
        Args:
            broker_type: 'alpaca', 'robinhood', etc.
            paper_trading: Use paper trading mode
        """
        self.broker_type = broker_type
        
        if broker_type == 'alpaca':
            self.broker = AlpacaBroker(
                paper_trading=paper_trading,
                **kwargs
            )
        else:
            raise ValueError(f"Unknown broker type: {broker_type}")
    
    def place_buy_order(self, symbol: str, shares: int, **kwargs):
        return self.broker.place_buy_order(symbol, shares, **kwargs)
    
    def place_sell_order(self, symbol: str, shares: int, **kwargs):
        return self.broker.place_sell_order(symbol, shares, **kwargs)
    
    def get_account_balance(self) -> float:
        return self.broker.get_account_balance()
    
    def get_positions(self) -> Dict:
        return self.broker.get_positions()
    
    def get_order_status(self, order_id: str) -> Dict:
        return self.broker.get_order_status(order_id)
