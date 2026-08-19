"""
Logging utilities for Automation Center Backend.
Provides structured logging with automatic sanitization of sensitive data.
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from .security import log_sanitizer

class SanitizingFormatter(logging.Formatter):
    """Custom formatter that sanitizes sensitive data in log messages."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Sanitize the message if it's a dict
        if isinstance(record.msg, dict):
            record.msg = log_sanitizer.sanitize_dict(record.msg)
        
        # Sanitize the message if it's a string
        if isinstance(record.msg, str):
            record.msg = log_sanitizer.sanitize_string(record.msg)
        
        # Sanitize the args
        if record.args:
            if isinstance(record.args, dict):
                record.args = log_sanitizer.sanitize_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    log_sanitizer.sanitize_dict(arg) if isinstance(arg, dict)
                    else log_sanitizer.sanitize_string(arg) if isinstance(arg, str)
                    else arg
                    for arg in record.args
                )
        
        return super().format(record)

class SanitizingFilter(logging.Filter):
    """Filter that sanitizes sensitive data before logging."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Sanitize the record message
        if isinstance(record.msg, dict):
            record.msg = log_sanitizer.sanitize_dict(record.msg)
        
        # Sanitize the args
        if record.args:
            if isinstance(record.args, dict):
                record.args = log_sanitizer.sanitize_dict(record.args)
        
        return True

class Logger:
    """Wrapper around Python logging with automatic sanitization."""
    
    _instance: Optional['Logger'] = None
    
    def __new__(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._logger = logging.getLogger("automation-center")
        self._logger.setLevel(logging.DEBUG)
        
        # Console handler with sanitizing formatter
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = SanitizingFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(SanitizingFilter())
        self._logger.addHandler(console_handler)
    
    def debug(self, message: str, **kwargs):
        """Log a debug message."""
        if kwargs:
            self._logger.debug(f"{message} | " + " ".join(f"{k}={v}" for k, v in kwargs.items()))
        else:
            self._logger.debug(message)
    
    def info(self, message: str, **kwargs):
        """Log an info message."""
        if kwargs:
            self._logger.info(f"{message} | " + " ".join(f"{k}={v}" for k, v in kwargs.items()))
        else:
            self._logger.info(message)
    
    def warning(self, message: str, **kwargs):
        """Log a warning message."""
        if kwargs:
            self._logger.warning(f"{message} | " + " ".join(f"{k}={v}" for k, v in kwargs.items()))
        else:
            self._logger.warning(message)
    
    def error(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        """Log an error message."""
        if kwargs:
            self._logger.error(f"{message} | " + " ".join(f"{k}={v}" for k, v in kwargs.items()))
        else:
            self._logger.error(message)
        
        if exc_info:
            self._logger.exception(exc_info)
    
    def critical(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        """Log a critical message."""
        if kwargs:
            self._logger.critical(f"{message} | " + " ".join(f"{k}={v}" for k, v in kwargs.items()))
        else:
            self._logger.critical(message)
        
        if exc_info:
            self._logger.exception(exc_info)

# Global logger instance
logger = Logger()