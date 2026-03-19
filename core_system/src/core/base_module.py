"""
Base classes and interfaces for all modules.
Ensures consistent behavior and clear contracts.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging


class BaseModule(ABC):
    """
    Base class for all trading system modules.
    
    Provides consistent logging, error handling, and lifecycle management.
    """
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        """
        Initialize module.
        
        Args:
            name: Module name (for logging)
            logger: Logger instance
        """
        self.name = name
        self.logger = logger or logging.getLogger(name)
        self.is_initialized = False
        self.errors: List[str] = []
    
    def initialize(self) -> bool:
        """Initialize module - override in subclasses."""
        self.is_initialized = True
        self.logger.info(f"{self.name} initialized")
        return True
    
    def shutdown(self) -> bool:
        """Shutdown module - override in subclasses."""
        self.is_initialized = False
        self.logger.info(f"{self.name} shutdown")
        return True
    
    def log_error(self, error: str) -> None:
        """Log an error."""
        self.errors.append(error)
        self.logger.error(f"{self.name}: {error}")
    
    def health_check(self) -> Dict[str, Any]:
        """Return module health status."""
        return {
            'name': self.name,
            'initialized': self.is_initialized,
            'errors': len(self.errors),
            'last_errors': self.errors[-5:] if self.errors else []
        }
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate module is working correctly."""
        pass
