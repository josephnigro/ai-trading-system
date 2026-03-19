"""Trade logging and reporting."""

import json
import csv
from datetime import datetime
from typing import Dict, List
import os


class TradeLogger:
    """Logs trades to file for record-keeping and analysis."""
    
    def __init__(self, log_dir: str = 'trade_logs'):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self.log_file = os.path.join(log_dir, f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
        self.trades: List[Dict] = []
    
    def log_trade(self, trade_data: Dict) -> None:
        """Log a trade."""
        trade_data['timestamp'] = datetime.now().isoformat()
        self.trades.append(trade_data)
        
        # Write to CSV
        if not os.path.exists(self.log_file) or os.path.getsize(self.log_file) == 0:
            # Write header
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=trade_data.keys())
                writer.writeheader()
                writer.writerow(trade_data)
        else:
            # Append row
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=trade_data.keys())
                writer.writerow(trade_data)
    
    def get_trades(self) -> List[Dict]:
        """Get all logged trades."""
        return self.trades.copy()
