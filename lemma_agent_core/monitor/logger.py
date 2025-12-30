"""
Agent Logger - Unified Logging with Loguru
===========================================
This module provides a unified logging interface using loguru.
It supports task-specific logging, multiple log levels, and flexible configuration.
"""

import json
import sys
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union
from loguru import logger
import contextvars
from copy import deepcopy


LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[task_id]} | {name}:{function}:{line} + {message}{exception}"

# Context variable for task_id to support async environments
_task_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('task_id', default=None)


class AgentLogger:
    """
    Unified logger for Lemma Toolkit using loguru.
    Supports task-specific logging and provides a clean interface.
    """
    
    _initialized = False
    _log_dir: Optional[Path] = None

    def __init__(self, task_id: Optional[str] = None):
        """
        Initialize AgentLogger
        
        Args:
            task_id: Optional task identifier for scoped logging
        """
        self._task_id: Optional[str] = None
        
        # Initialize loguru on first use
        if not AgentLogger._initialized:
            self._setup_default_logger()

        if task_id:
            self.set_task_id(task_id)
    
    @staticmethod
    def _patch_record(record):
        """Ensure common metadata is present on each log record."""
        extra = record["extra"]

        if extra.get("task_id") in (None, ""):
            context_task_id = _task_id_context.get()
            extra["task_id"] = context_task_id or "NO-TASK"

        file_path = record.get("file")
        if file_path is not None:
            try:
                path_obj = Path(file_path.path).resolve()
                cwd = Path.cwd().resolve()
                extra["file_path"] = path_obj.relative_to(cwd).as_posix()
            except Exception:
                extra["file_path"] = Path(file_path.path).as_posix()
        else:
            extra.setdefault("file_path", "<unknown>")

        # Ensure llm_event metadata doesn't raise KeyErrors in formatters
        if "llm_event" not in extra:
            extra["llm_event"] = None
    
    @staticmethod
    def _sanitize_base64_content(data: Any) -> Any:
        """
        Recursively replace base64 content with '<base64_content>' placeholder.
        
        This prevents log files from becoming bloated with large base64-encoded
        images or PDFs while still showing the structure of the data.
        
        Args:
            data: The data structure to sanitize (dict, list, or primitive)
            
        Returns:
            A sanitized copy of the data with base64 content replaced
        """
        if isinstance(data, dict):
            # Create a shallow copy to avoid modifying the original
            result = {}
            for key, value in data.items():
                # Check if this looks like a base64 data field
                if key == "data" and isinstance(value, str):
                    # Check if the parent dict has source.type == "base64" pattern
                    # or if this is a long string that looks like base64
                    if len(value) > 100 and re.match(r'^[A-Za-z0-9+/=]+$', value[:100]):
                        result[key] = "<base64_content>"
                        continue
                
                # Recursively sanitize nested structures
                result[key] = AgentLogger._sanitize_base64_content(value)
            return result
            
        elif isinstance(data, (list, tuple)):
            # Recursively sanitize list/tuple items
            result = [AgentLogger._sanitize_base64_content(item) for item in data]
            return result if isinstance(data, list) else tuple(result)
            
        else:
            # Return primitives as-is
            return data

    @classmethod
    def _setup_default_logger(cls):
        """Setup default loguru configuration"""
        if cls._initialized:
            return
        
        # Remove default handler
        logger.remove()

        # Ensure consistent record metadata
        logger.configure(patcher=cls._patch_record)
        
        # Add console handler with custom format
        logger.add(
            sys.stdout,
            format=LOG_FORMAT,
            level="DEBUG",
            filter=lambda record: record["extra"].get("task_id") not in (None, "NO-TASK")
        )
        
        # Add a fallback handler for logs without task_id
        logger.add(
            sys.stdout,
            format=LOG_FORMAT,
            level="DEBUG",
            filter=lambda record: record["extra"].get("task_id") in (None, "NO-TASK")
        )
        
        cls._initialized = True
    
    @classmethod
    def setup(
        cls,
        log_dir: Optional[Union[str, Path]] = None,
        console: bool = True,
        level: str = "INFO",
        rotation: str = "10 MB",
        retention: int = 5,
        compression: str = "zip"
    ):
        """
        Setup loguru logging with custom configuration
        
        Args:
            log_dir: Directory for log files (optional)
            console: Whether to output to console
            level: Logging level (TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL)
            rotation: When to rotate log files (e.g., "10 MB", "1 week", "00:00")
            retention: Number of rotated log files to keep (e.g., 5 keeps the 5 most recent)
            compression: Compression format for rotated logs (e.g., "zip", "tar.gz")
        """
        # Remove all existing handlers
        logger.remove()

        # Ensure consistent record metadata
        logger.configure(patcher=cls._patch_record)
        
        cls._log_dir = Path(log_dir) if log_dir else None
        
        # Add console handler if requested
        if console:
            logger.add(
                sys.stdout,
                format=LOG_FORMAT,
                level=level,
                filter=lambda record: record["extra"].get("task_id") not in (None, "NO-TASK")
            )
            
            # Fallback handler for logs without task_id
            logger.add(
                sys.stdout,
                format=LOG_FORMAT,
                level=level,
                filter=lambda record: record["extra"].get("task_id") in (None, "NO-TASK")
            )
        
        # Add file handlers if log directory specified
        if cls._log_dir:
            cls._log_dir.mkdir(parents=True, exist_ok=True)
            
            # Main log file (all levels)
            logger.add(
                cls._log_dir / "agent.log",
                format=LOG_FORMAT,
                level="DEBUG",
                rotation=rotation,
                retention=retention,
                compression=compression,
                filter=lambda record: record["extra"].get("task_id") not in (None, "NO-TASK")
            )
            
            # Fallback file handler
            logger.add(
                cls._log_dir / "agent.log",
                format=LOG_FORMAT,
                level="DEBUG",
                rotation=rotation,
                retention=retention,
                compression=compression,
                filter=lambda record: record["extra"].get("task_id") in (None, "NO-TASK")
            )
            
            # Error log file (only errors and critical)
            logger.add(
                cls._log_dir / "error.log",
                format=LOG_FORMAT,
                level="ERROR",
                rotation=rotation,
                retention=retention,
                compression=compression,
                backtrace=True,
                diagnose=True,
                filter=lambda record: record["extra"].get("task_id") not in (None, "NO-TASK")
            )
            
            # Fallback error handler
            logger.add(
                cls._log_dir / "error.log",
                format=LOG_FORMAT,
                level="ERROR",
                rotation=rotation,
                retention=retention,
                compression=compression,
                backtrace=True,
                diagnose=True,
                filter=lambda record: record["extra"].get("task_id") in (None, "NO-TASK")
            )

            # Dedicated LLM interaction log file for easier tracing
            logger.add(
                cls._log_dir / "llm.log",
                format=LOG_FORMAT,
                level="DEBUG",
                rotation=rotation,
                retention=retention,
                compression=compression,
                filter=lambda record: record["extra"].get("llm_event") is not None
            )
        
        cls._initialized = True

    def _log_llm_event(self, marker: str, payload: Dict[str, Any], level: str = "INFO"):
        """Internal helper to log LLM-related payloads with a consistent marker."""
        bound_logger = self._get_logger().bind(llm_event=marker.lower())
        log_method = getattr(bound_logger, level.lower(), None) or bound_logger.info
        
        # Sanitize base64 content before logging to prevent log bloat
        sanitized_payload = self._sanitize_base64_content(payload)
        
        entry = {
            "event": marker,
            "payload": sanitized_payload,
        }
        try:
            serialized_payload = json.dumps(entry, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            serialized_payload = json.dumps({"event": marker, "payload": str(sanitized_payload)}, ensure_ascii=False)
        log_method("{}", serialized_payload)

    def _log_with_exception_support(self, level: str, message: str, *args, **kwargs) -> None:
        """Emit log while ensuring active exceptions include stack traces."""
        exception_param = kwargs.pop("exception", None)
        exc_info_flag = kwargs.pop("exc_info", False)

        exc_object: Any = None
        if isinstance(exception_param, BaseException):
            exc_object = exception_param
        elif exception_param:
            exc_object = True

        if exc_object is None and exc_info_flag:
            exc_object = True

        if exc_object is None and sys.exc_info()[0] is not None:
            exc_object = True

        logger_instance = self._get_logger()
        if exc_object is not None:
            emitter = getattr(logger_instance.opt(exception=exc_object), level)
        else:
            emitter = getattr(logger_instance, level)

        emitter(message, *args, **kwargs)

    def llm_request(
        self,
        *,
        model: str,
        messages: Sequence[Any],
        parameters: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[Any] = None,
        tools: Optional[Sequence[Any]] = None,
        level: str = "INFO",
        business: str = None,
        **extra: Any,
    ):
        """Log an LLM request with full context including parameters and messages."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        if system_prompt is not None:
            payload["system_prompt"] = system_prompt

        if parameters:
            payload["parameters"] = parameters

        if tools:
            payload["tools"] = tools

        if business:
            payload["business"] = business

        if extra:
            payload["extra"] = extra

        self._log_llm_event("LLM_CALL", payload, level=level)

    def llm_response(
        self,
        *,
        model: str,
        response: Any,
        usage: Optional[Dict[str, Any]] = None,
        level: str = "INFO",
        business: str = None,
        **extra: Any,
    ):
        """Log an LLM response payload including usage statistics."""
        payload: Dict[str, Any] = {
            "model": model,
            "response": response,
        }

        if usage:
            payload["usage"] = usage
            
        if business:
            payload["business"] = business

        if extra:
            payload["extra"] = extra

        self._log_llm_event("LLM_RESPONSE", payload, level=level)
    
    def set_task_id(self, task_id: str):
        """
        Set task ID for this logger instance
        
        Args:
            task_id: Task identifier
        """
        self._task_id = task_id
        _task_id_context.set(task_id)
    
    def get_task_id(self) -> Optional[str]:
        """Get current task ID"""
        return self._task_id or _task_id_context.get()
    
    @contextmanager
    def task_scope(self, task_id: str):
        """Temporarily set task_id for logs within this scope."""
        previous_local = self._task_id
        token = _task_id_context.set(task_id)
        self._task_id = task_id
        try:
            yield self
        finally:
            self._task_id = previous_local
            _task_id_context.reset(token)
    
    def _get_logger(self):
        """Get logger instance with task_id context"""
        task_id = self.get_task_id() or "NO-TASK"
        return logger.bind(task_id=task_id)
    
    # Logging methods
    
    def trace(self, message: str, *args, **kwargs):
        """Log trace message (most detailed)"""
        self._get_logger().trace(message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message"""
        self._get_logger().debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message"""
        self._get_logger().info(message, *args, **kwargs)
    
    def success(self, message: str, *args, **kwargs):
        """Log success message"""
        self._get_logger().success(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message"""
        self._get_logger().warning(message, *args, **kwargs)
    
    def warn(self, message: str, *args, **kwargs):
        """Alias for warning"""
        self.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message"""
        self._log_with_exception_support("error", message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message"""
        self._log_with_exception_support("critical", message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception with traceback"""
        self._get_logger().exception(message, *args, **kwargs)
    
    # Context managers
    
    def catch(self, *args, **kwargs):
        """
        Context manager to catch exceptions and log them
        
        Usage:
            with logger.catch():
                # code that might raise exceptions
        """
        return self._get_logger().catch(*args, **kwargs)
    
    def contextualize(self, **kwargs):
        """
        Context manager to add extra context to logs
        
        Usage:
            with logger.contextualize(user_id="123"):
                logger.info("User action")  # Will include user_id in log
        """
        return self._get_logger().contextualize(**kwargs)


# Module-level convenience functions

def setup_logging(
    log_dir: Optional[Union[str, Path]] = None,
    console: bool = True,
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "7 days",
    compression: str = "zip"
):
    """
    Setup loguru logging (convenience function)
    
    Args:
        log_dir: Directory for log files (optional)
        console: Whether to output to console
        level: Logging level (TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL)
        rotation: When to rotate log files
        retention: How long to keep old log files
        compression: Compression format for rotated logs
    """
    AgentLogger.setup(
        log_dir=log_dir,
        console=console,
        level=level,
        rotation=rotation,
        retention=retention,
        compression=compression
    )


def get_logger(task_id: Optional[str] = None) -> AgentLogger:
    """
    Get a logger instance (convenience function)
    
    Args:
        task_id: Optional task identifier
    
    Returns:
        AgentLogger instance
    """
    return AgentLogger(task_id=task_id)

