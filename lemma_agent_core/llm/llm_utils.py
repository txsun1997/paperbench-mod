"""Utility functions for LLM operations"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from monitor.logger import AgentLogger


def create_retry_logger(logger: 'AgentLogger'):
    """Create a retry logger callback that uses AgentLogger.
    
    This factory function creates a callback for tenacity retry operations
    that logs retry attempts using the provided AgentLogger instance.
    
    Args:
        logger: AgentLogger instance for logging
        
    Returns:
        A callback function that can be used with tenacity's before_sleep parameter
    """
    def log_retry_attempt(retry_state) -> None:
        """Log retry attempts for tenacity retry operations.
        
        Args:
            retry_state: The retry state object from tenacity
        """
        exception = retry_state.outcome.exception()

        # Add retry attempt and max retries to the exception for later use
        if hasattr(retry_state, 'retry_object') and hasattr(
            retry_state.retry_object, 'stop'
        ):
            # Get the max retries from the stop_after_attempt
            stop_condition = retry_state.retry_object.stop

            # Handle both single stop conditions and stop_any (combined conditions)
            stop_funcs = []
            if hasattr(stop_condition, 'stops'):
                # This is a stop_any object with multiple stop conditions
                stop_funcs = stop_condition.stops
            else:
                # This is a single stop condition
                stop_funcs = [stop_condition]

            for stop_func in stop_funcs:
                if hasattr(stop_func, 'max_attempts'):
                    # Add retry information to the exception
                    exception.retry_attempt = retry_state.attempt_number
                    exception.max_retries = stop_func.max_attempts
                    break

        # Get wait time - compatible with different tenacity versions
        if hasattr(retry_state, 'idle_for'):
            wait_time = retry_state.idle_for
        elif hasattr(retry_state, 'next_action') and hasattr(retry_state.next_action, 'sleep'):
            wait_time = retry_state.next_action.sleep
        elif hasattr(retry_state, 'wait'):
            wait_time = retry_state.wait
        else:
            wait_time = None
        
        if wait_time is not None:
            logger.warning(
                f'{exception}. Attempt #{retry_state.attempt_number}, waiting {wait_time} seconds before next attempt.'
            )
        else:
            logger.warning(
                f'{exception}. Attempt #{retry_state.attempt_number}, retrying...'
            )
    
    return log_retry_attempt