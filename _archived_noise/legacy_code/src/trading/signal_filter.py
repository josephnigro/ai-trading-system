"""Signal filtering for quality control."""

from typing import List, Dict


class SignalFilter:
    """Filters trading signals for quality."""
    
    def __init__(self, min_score: float = 0.0):
        self.min_score = min_score
        self.filtered_signals: List[Dict] = []
    
    def filter_signals(self, signals: List[Dict]) -> List[Dict]:
        """Filter signals by quality criteria."""
        self.filtered_signals = []
        
        for signal in signals:
            # Check minimum score threshold
            score = signal.get('score', 0)
            if score < self.min_score:
                continue
            
            # Pass quality checks
            self.filtered_signals.append(signal)
        
        return self.filtered_signals
