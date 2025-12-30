"""
Unified Logging Configuration
==============================
This module provides unified logging configuration for the Lemma Toolkit using loguru.
It ensures consistent logging across all modules and provides both console
and file output capabilities with log rotation support.
"""

import sys
from pathlib import Path
from typing import Optional, Union
from loguru import logger as loguru_logger
from utils.user_manager import get_lemma_dir


class LoggerConfig:
    """Unified logger configuration for Lemma Toolkit using loguru"""

    _initialized = False
    _log_dir = None

    @classmethod
    def setup(cls, log_file: Optional[Path] = None, console: bool = True, level: str = "INFO",
              use_rotation: bool = False, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
        """
        Setup unified logging configuration using loguru

        Args:
            log_file: Path to log file (optional)
            console: Whether to output to console
            level: Logging level (TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL)
            use_rotation: Whether to use rotating file handler (default: False)
            max_bytes: Maximum size of each log file in bytes (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)
        """
        if cls._initialized:
            return

        cls._log_file = log_file

        # Remove default handler
        loguru_logger.remove()

        # Add console handler if requested
        if console:
            loguru_logger.add(
                sys.stdout,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                level=level,
                colorize=True
            )

        # Add file handler if log file specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)

            if use_rotation:
                # Use loguru rotation (convert bytes to MB for loguru)
                rotation_size = f"{max_bytes // (1024 * 1024)} MB"
                loguru_logger.add(
                    log_file,
                    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                    level=level,
                    rotation=rotation_size,
                    retention=backup_count,
                    compression="zip",
                    backtrace=True,
                    diagnose=True
                )
            else:
                # Regular file handler without rotation
                loguru_logger.add(
                    log_file,
                    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                    level=level,
                    backtrace=True,
                    diagnose=True
                )

        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str = None):
        """
        Get a logger instance
        
        Args:
            name: Logger name (optional, for compatibility)
        
        Returns:
            Loguru logger instance
        """
        if name:
            return loguru_logger.bind(name=name)
        return loguru_logger
    
    @classmethod
    def reset(cls):
        """Reset logger configuration"""
        loguru_logger.remove()
        cls._initialized = False
        cls._log_file = None


def setup_logging(log_file: Optional[Path] = None, console: bool = True, level: str = "INFO",
                  use_rotation: bool = False, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
    """
    Setup unified logging (convenience function)

    Args:
        log_file: Path to log file (optional)
        console: Whether to output to console
        level: Logging level (TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL)
        use_rotation: Whether to use rotating file handler (default: False)
        max_bytes: Maximum size of each log file in bytes (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
    """
    LoggerConfig.setup(log_file=log_file, console=console, level=level,
                       use_rotation=use_rotation, max_bytes=max_bytes, backup_count=backup_count)


def get_logger(name: str = None):
    """
    Get a logger instance (convenience function)
    
    Args:
        name: Logger name (optional, for compatibility)
    
    Returns:
        Loguru logger instance
    """
    return logging.getLogger(name)


def get_cli_log_file() -> Path:
    """
    Get CLI log file path

    Returns:
        Path to CLI log file
    """
    log_dir = get_lemma_dir() / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return (log_dir / 'cli.log').resolve()

# Setup logging for CLI - file only, no console output
# User-facing messages will use print() statements
# Use rotating log to prevent file from growing too large (max 10MB, keep 5 backups)
setup_logging(
    level='DEBUG',
    log_file=get_cli_log_file(),
    console=False,
    use_rotation=True,
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5
)