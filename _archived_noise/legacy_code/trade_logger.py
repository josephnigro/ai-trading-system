# ==============================
# TRADE LOGGER MODULE
# ==============================
# Logs all signals, trades, and outcomes for analysis

import json
import csv
from datetime import datetime
import os

class TradeLogger:
    """
    Logs all trading signals and executions
    Creates audit trail for analysis and compliance
    """
    
    def __init__(self, log_dir='trade_logs'):
        self.log_dir = log_dir
        self.ensure_log_dir()
        
        self.signals_log = []
        self.trades_log = []
        self.decisions_log = []
    
    def ensure_log_dir(self):
        """Create log directory if it doesn't exist"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def log_signal(self, ticker, signal_data, reason, approved=None):
        """
        Log a generated signal
        
        signal_data: Full signal dict from scanner
        reason: Why this signal was generated
        approved: True/False/None (pending)
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'signal_type': signal_data.get('signal'),
            'entry_price': signal_data.get('price'),
            'rsi': signal_data.get('technical', {}).get('rsi'),
            'macd_trend': signal_data.get('technical', {}).get('macd_trend'),
            'ma_trend': signal_data.get('technical', {}).get('ma_trend'),
            'ml_direction': signal_data.get('ml_prediction', {}).get('direction'),
            'ml_confidence': signal_data.get('ml_prediction', {}).get('confidence'),
            'sentiment': signal_data.get('sentiment', {}).get('overall_sentiment'),
            'reason': reason,
            'approved': approved,
            'status': 'PENDING' if approved is None else ('APPROVED' if approved else 'REJECTED')
        }
        
        self.signals_log.append(log_entry)
        self._save_signal_log()
        
        return log_entry
    
    def log_trade(self, trade_data):
        """
        Log an executed trade
        
        trade_data should contain:
        - ticker, entry_price, stop_loss, target
        - shares, risk_dollars, position_value
        - trade_id, timestamp, reason
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'trade_id': trade_data.get('trade_id', f"TRADE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            'ticker': trade_data.get('ticker'),
            'signal_type': trade_data.get('signal_type'),
            'entry_price': trade_data.get('entry_price'),
            'stop_loss': trade_data.get('stop_loss'),
            'target': trade_data.get('target'),
            'shares': trade_data.get('shares'),
            'position_value': trade_data.get('position_value'),
            'risk_dollars': trade_data.get('risk_dollars'),
            'reason': trade_data.get('reason'),
            'execution_strategy': trade_data.get('execution_strategy', 'MANUAL'),
            'status': 'OPEN'
        }
        
        self.trades_log.append(log_entry)
        self._save_trade_log()
        
        print(f"\n✓ TRADE LOGGED:")
        print(f"  Ticker: {log_entry['ticker']}")
        print(f"  Entry: ${log_entry['entry_price']:.2f}")
        print(f"  Stop: ${log_entry['stop_loss']:.2f}")
        print(f"  Target: ${log_entry['target']:.2f}")
        print(f"  Shares: {log_entry['shares']}")
        print(f"  Risk: ${log_entry['risk_dollars']:.2f}")
        
        return log_entry
    
    def log_decision(self, description, decision_type, data=None):
        """
        Log system decisions (approvals, rejections, overrides)
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'decision_type': decision_type,  # APPROVE, REJECT, OVERRIDE, HALT
            'description': description,
            'data': data or {}
        }
        
        self.decisions_log.append(log_entry)
        self._save_decision_log()
    
    def close_trade(self, trade_id, exit_price, reason):
        """
        Close a trade and record P&L
        """
        # Find trade
        trade = next((t for t in self.trades_log if t['trade_id'] == trade_id), None)
        
        if not trade:
            print(f"Trade {trade_id} not found")
            return None
        
        # Calculate P&L
        pnl_dollars = (exit_price - trade['entry_price']) * trade['shares']
        pnl_percent = (exit_price - trade['entry_price']) / trade['entry_price'] * 100
        
        # Update trade
        trade['exit_price'] = exit_price
        trade['exit_reason'] = reason
        trade['pnl_dollars'] = pnl_dollars
        trade['pnl_percent'] = pnl_percent
        trade['status'] = 'CLOSED'
        trade['exit_timestamp'] = datetime.now().isoformat()
        
        self._save_trade_log()
        
        print(f"\n✓ TRADE CLOSED:")
        print(f"  Ticker: {trade['ticker']}")
        print(f"  P&L: ${pnl_dollars:.2f} ({pnl_percent:.2f}%)")
        print(f"  Reason: {reason}")
        
        return trade
    
    def _save_signal_log(self):
        """Save signals to CSV"""
        if not self.signals_log:
            return
        
        filename = os.path.join(self.log_dir, f"signals_{datetime.now().strftime('%Y%m%d')}.csv")
        
        keys = self.signals_log[0].keys()
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.signals_log)
    
    def _save_trade_log(self):
        """Save trades to CSV"""
        if not self.trades_log:
            return
        
        filename = os.path.join(self.log_dir, f"trades_{datetime.now().strftime('%Y%m%d')}.csv")
        
        keys = self.trades_log[0].keys() if self.trades_log else []
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.trades_log)
    
    def _save_decision_log(self):
        """Save decisions to JSON"""
        if not self.decisions_log:
            return
        
        filename = os.path.join(self.log_dir, f"decisions_{datetime.now().strftime('%Y%m%d')}.json")
        
        with open(filename, 'w') as f:
            json.dump(self.decisions_log, f, indent=2)
    
    def get_trade_performance(self):
        """
        Analyze closed trades and return performance metrics
        """
        closed_trades = [t for t in self.trades_log if t['status'] == 'CLOSED']
        
        if not closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        pnl_list = [t['pnl_dollars'] for t in closed_trades]
        wins = [p for p in pnl_list if p > 0]
        losses = [p for p in pnl_list if p < 0]
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': (len(wins) / len(closed_trades) * 100) if closed_trades else 0,
            'total_pnl': sum(pnl_list),
            'avg_pnl': sum(pnl_list) / len(closed_trades),
            'best_trade': max(pnl_list) if pnl_list else 0,
            'worst_trade': min(pnl_list) if pnl_list else 0,
            'profit_factor': sum(wins) / abs(sum(losses)) if losses else 0
        }
    
    def print_performance_report(self):
        """Print performance analysis"""
        perf = self.get_trade_performance()
        
        print("\n" + "="*60)
        print("TRADING PERFORMANCE REPORT")
        print("="*60)
        print(f"Total Trades: {perf['total_trades']}")
        print(f"Winning Trades: {perf['winning_trades']}")
        print(f"Losing Trades: {perf['losing_trades']}")
        print(f"Win Rate: {perf['win_rate']:.1f}%")
        print(f"Total P&L: ${perf['total_pnl']:.2f}")
        print(f"Average P&L: ${perf['avg_pnl']:.2f}")
        print(f"Best Trade: ${perf['best_trade']:.2f}")
        print(f"Worst Trade: ${perf['worst_trade']:.2f}")
        print(f"Profit Factor: {perf['profit_factor']:.2f}x")
        print("="*60)
