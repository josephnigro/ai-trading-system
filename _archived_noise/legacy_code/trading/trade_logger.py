"""Logging for trades, signals, and system decisions."""

import json
import csv
from datetime import datetime
import os


class TradeLogger:
    """Logs signals, trades, and decisions for audit trail."""
    
    def __init__(self, log_dir='trade_logs'):
        self.log_dir = log_dir
        self._ensure_log_dir()
        self.signals_log = []
        self.trades_log = []
        self.decisions_log = []
    
    def _ensure_log_dir(self):
        """Create log directory if needed."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def log_signal(self, ticker, signal_data, reason, approved=None):
        """Log a generated signal."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'signal_type': signal_data.get('signal'),
            'entry_price': signal_data.get('price'),
            'rsi': signal_data.get('technical', {}).get('rsi'),
            'macd_trend': signal_data.get('technical', {}).get('macd_trend'),
            'ml_direction': signal_data.get('ml_prediction', {}).get('direction'),
            'sentiment': signal_data.get('sentiment', {}).get('overall_sentiment'),
            'reason': reason,
            'status': 'PENDING' if approved is None else ('APPROVED' if approved else 'REJECTED')
        }
        
        self.signals_log.append(log_entry)
        self._save_signal_log()
        return log_entry
    
    def log_trade(self, trade_data):
        """Log an executed trade."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'trade_id': trade_data.get('trade_id', f"TRADE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            'ticker': trade_data.get('ticker'),
            'entry_price': trade_data.get('entry_price'),
            'stop_loss': trade_data.get('stop_loss'),
            'target': trade_data.get('target'),
            'shares': trade_data.get('shares'),
            'risk_dollars': trade_data.get('risk_dollars'),
            'status': 'OPEN'
        }
        
        self.trades_log.append(log_entry)
        self._save_trade_log()
        
        print(f"\n✓ TRADE LOGGED: {log_entry['ticker']}")
        print(f"  Entry: ${log_entry['entry_price']:.2f} | Stop: ${log_entry['stop_loss']:.2f}")
        print(f"  Risk: ${log_entry['risk_dollars']:.2f}")
        
        return log_entry
    
    def log_decision(self, description, decision_type, data=None):
        """Log system decisions."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'decision_type': decision_type,
            'description': description,
            'data': data or {}
        }
        self.decisions_log.append(log_entry)
        self._save_decision_log()
    
    def close_trade(self, trade_id, exit_price, reason):
        """Close a trade and record P&L."""
        trade = next((t for t in self.trades_log if t['trade_id'] == trade_id), None)
        
        if not trade:
            return None
        
        pnl_dollars = (exit_price - trade['entry_price']) * trade['shares']
        pnl_percent = (exit_price - trade['entry_price']) / trade['entry_price'] * 100
        
        trade['exit_price'] = exit_price
        trade['pnl_dollars'] = pnl_dollars
        trade['pnl_percent'] = pnl_percent
        trade['status'] = 'CLOSED'
        
        self._save_trade_log()
        
        print(f"\n✓ TRADE CLOSED: {trade['ticker']}")
        print(f"  P&L: ${pnl_dollars:.2f} ({pnl_percent:.2f}%)")
        
        return trade
    
    def _save_signal_log(self):
        """Save signals to CSV."""
        if not self.signals_log:
            return
        
        filename = os.path.join(self.log_dir, f"signals_{datetime.now().strftime('%Y%m%d')}.csv")
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.signals_log[0].keys())
            writer.writeheader()
            writer.writerows(self.signals_log)
    
    def _save_trade_log(self):
        """Save trades to CSV."""
        if not self.trades_log:
            return
        
        filename = os.path.join(self.log_dir, f"trades_{datetime.now().strftime('%Y%m%d')}.csv")
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.trades_log[0].keys())
            writer.writeheader()
            writer.writerows(self.trades_log)
    
    def _save_decision_log(self):
        """Save decisions to JSON."""
        if not self.decisions_log:
            return
        
        filename = os.path.join(self.log_dir, f"decisions_{datetime.now().strftime('%Y%m%d')}.json")
        with open(filename, 'w') as f:
            json.dump(self.decisions_log, f, indent=2)
    
    def get_trade_performance(self):
        """Analyze closed trades."""
        closed = [t for t in self.trades_log if t['status'] == 'CLOSED']
        
        if not closed:
            return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0}
        
        pnls = [t['pnl_dollars'] for t in closed]
        wins = [p for p in pnls if p > 0]
        
        return {
            'total_trades': len(closed),
            'winning_trades': len(wins),
            'win_rate': (len(wins) / len(closed) * 100),
            'total_pnl': sum(pnls),
            'avg_pnl': sum(pnls) / len(closed),
        }
