"""
Logging module - audit trails and reporting.
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from ..core.base_module import BaseModule


class LoggingModule(BaseModule):
    """
    Central logging module for audit trail.
    Logs signals, proposals, executions.
    """
    
    def __init__(self, logs_dir: str = "logs"):
        super().__init__("LoggingModule")
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        self.session_log = []
    
    def log_signal(self, signal_data: Dict) -> None:
        """Log a signal."""
        self.session_log.append({
            'type': 'SIGNAL',
            'timestamp': datetime.utcnow().isoformat(),
            'data': signal_data
        })
    
    def log_proposal(self, proposal_data: Dict) -> None:
        """Log a proposal."""
        self.session_log.append({
            'type': 'PROPOSAL',
            'timestamp': datetime.utcnow().isoformat(),
            'data': proposal_data
        })
    
    def log_execution(self, execution_data: Dict) -> None:
        """Log an execution."""
        self.session_log.append({
            'type': 'EXECUTION',
            'timestamp': datetime.utcnow().isoformat(),
            'data': execution_data
        })
    
    def log_approval(self, trade_id: str, approved: bool, notes: str = "") -> None:
        """Log user approval/rejection."""
        self.session_log.append({
            'type': 'APPROVAL',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'trade_id': trade_id,
                'approved': approved,
                'notes': notes
            }
        })
    
    def save_session_log(self, session_name: Optional[str] = None) -> str:
        """Save session log to JSON file."""
        if not session_name:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        log_file = self.logs_dir / f"session_{session_name}.json"
        
        with open(log_file, 'w') as f:
            json.dump(self.session_log, f, indent=2)
        
        return str(log_file)
    
    def validate(self) -> bool:
        """Validate logging is working."""
        try:
            test_file = self.logs_dir / "test.txt"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception as e:
            self.log_error(f"Logging validation failed: {str(e)}")
            return False
