"""
# ============================================================================
# ALPACA BROKER MODULE
# ============================================================================
# Clean integration with Alpaca REST API for orders and account management
# ============================================================================
"""

import os
import requests
from datetime import datetime
from typing import Optional, Dict, List


# ============================================================================
# CONFIGURATION
# ============================================================================

ALPACA_URL_PAPER = "https://paper-api.alpaca.markets"
ALPACA_URL_LIVE = "https://api.alpaca.markets"
REQUEST_TIMEOUT = 10


# ============================================================================
# ALPACA BROKER CLASS
# ============================================================================

class AlpacaBroker:
    """
    Direct REST API integration with Alpaca brokerage.
    
    Features:
    - Paper trading ($100k virtual capital)
    - Live trading with as little as $1
    - Commission-free trading
    - Penny stock support
    - Easy setup (no approval delays)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        paper_trading: bool = True
    ):
        """
        Initialize Alpaca broker connection.
        
        Args:
            api_key: Alpaca API key (defaults to ALPACA_API_KEY env var)
            api_secret: Alpaca API secret (defaults to ALPACA_API_SECRET env var)
            paper_trading: Use paper trading if True, live if False
        """
        self.api_key = api_key or os.getenv('ALPACA_API_KEY')
        self.api_secret = api_secret or os.getenv('ALPACA_API_SECRET')
        self.paper_trading = paper_trading
        
        # Set API endpoint
        self.base_url = ALPACA_URL_PAPER if paper_trading else ALPACA_URL_LIVE
        
        # State
        self.connected = False
        self.account = None
        self.orders: Dict[str, Dict] = {}
        
        # Try to connect
        self._connect()
    
    # ========================================================================
    # CONNECTION
    # ========================================================================
    
    def _connect(self) -> bool:
        """
        Test connection to Alpaca API.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            # Log connection attempt
            mode = "PAPER" if self.paper_trading else "LIVE"
            print(f"[INFO] Connecting to Alpaca ({mode})...")
            
            # Check for credentials
            if not self.api_key or not self.api_secret:
                print("[ERR] Missing API key or secret in environment")
                return False
            
            # Test connection
            response = self._make_request('GET', '/v2/account')
            
            if response and 'status' in response:
                self.account = response
                self.connected = True
                balance = float(response.get('buying_power', 0))
                print(f"[OK] Connected! Account balance: ${balance:,.2f}")
                return True
            else:
                print("[ERR] Failed to retrieve account info")
                return False
                
        except Exception as e:
            print(f"[ERR] Connection failed: {e}")
            return False
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make authenticated request to Alpaca API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/v2/orders')
            data: Request body for POST/PUT
            
        Returns:
            Response JSON or None if failed
        """
        try:
            headers = {
                'APCA-API-KEY-ID': self.api_key,
                'APCA-API-SECRET-KEY': self.api_secret,
                'Content-Type': 'application/json'
            }
            
            url = self.base_url + endpoint
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=REQUEST_TIMEOUT)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)
            else:
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"[ERR] API error: {e}")
            return None
        except Exception as e:
            print(f"[ERR] Request failed: {e}")
            return None
    
    # ========================================================================
    # ORDERS
    # ========================================================================
    
    def place_buy_order(
        self,
        symbol: str,
        shares: int,
        limit_price: Optional[float] = None
    ) -> Dict:
        """
        Place a buy order.
        
        Args:
            symbol: Stock ticker
            shares: Number of shares
            limit_price: Limit price (market order if None)
            
        Returns:
            Dict with order confirmation or error
        """
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        
        try:
            order_data = {
                'symbol': symbol,
                'qty': shares,
                'side': 'buy',
                'type': 'limit' if limit_price else 'market',
                'time_in_force': 'day'
            }
            if limit_price:
                order_data['limit_price'] = limit_price
            
            response = self._make_request('POST', '/v2/orders', order_data)
            
            if response and 'id' in response:
                order_id = response['id']
                self.orders[order_id] = {
                    'symbol': symbol,
                    'shares': shares,
                    'side': 'buy',
                    'price': limit_price or 'market',
                    'status': response.get('status'),
                    'timestamp': datetime.now()
                }
                
                price_str = f"${limit_price:.2f}" if limit_price else "market"
                print(f"[OK] BUY {shares} {symbol} @ {price_str}")
                return {
                    'success': True,
                    'order_id': order_id,
                    'symbol': symbol,
                    'shares': shares
                }
            else:
                error = response.get('message') if response else 'Unknown error'
                print(f"[ERR] Order failed: {error}")
                return {'success': False, 'error': error}
                
        except Exception as e:
            print(f"[ERR] {e}")
            return {'success': False, 'error': str(e)}
    
    def place_sell_order(
        self,
        symbol: str,
        shares: int,
        limit_price: Optional[float] = None
    ) -> Dict:
        """
        Place a sell order.
        
        Args:
            symbol: Stock ticker
            shares: Number of shares
            limit_price: Limit price (market order if None)
            
        Returns:
            Dict with order confirmation or error
        """
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        
        try:
            order_data = {
                'symbol': symbol,
                'qty': shares,
                'side': 'sell',
                'type': 'limit' if limit_price else 'market',
                'time_in_force': 'day'
            }
            if limit_price:
                order_data['limit_price'] = limit_price
            
            response = self._make_request('POST', '/v2/orders', order_data)
            
            if response and 'id' in response:
                order_id = response['id']
                self.orders[order_id] = {
                    'symbol': symbol,
                    'shares': shares,
                    'side': 'sell',
                    'price': limit_price or 'market',
                    'status': response.get('status'),
                    'timestamp': datetime.now()
                }
                
                price_str = f"${limit_price:.2f}" if limit_price else "market"
                print(f"[OK] SELL {shares} {symbol} @ {price_str}")
                return {
                    'success': True,
                    'order_id': order_id,
                    'symbol': symbol,
                    'shares': shares
                }
            else:
                error = response.get('message') if response else 'Unknown error'
                print(f"[ERR] Order failed: {error}")
                return {'success': False, 'error': error}
                
        except Exception as e:
            print(f"[ERR] {e}")
            return {'success': False, 'error': str(e)}
    
    # ========================================================================
    # ACCOUNT INFO
    # ========================================================================
    
    def get_balance(self) -> float:
        """
        Get current account buying power.
        
        Returns:
            Balance in dollars
        """
        if self.account:
            return float(self.account.get('buying_power', 0))
        return 0.0
    
    def get_positions(self) -> Dict[str, Dict]:
        """
        Get current open positions.
        
        Returns:
            Dictionary of positions by symbol
        """
        try:
            response = self._make_request('GET', '/v2/positions')
            if response and isinstance(response, list):
                positions = {}
                for pos in response:
                    symbol = pos.get('symbol')
                    positions[symbol] = {
                        'qty': float(pos.get('qty', 0)),
                        'avg_fill_price': float(pos.get('avg_fill_price', 0)),
                        'current_price': float(pos.get('current_price', 0))
                    }
                return positions
            return {}
        except Exception as e:
            print(f"Error getting positions: {e}")
            return {}
