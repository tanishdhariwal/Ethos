"""Retry and error handling utilities for robust API calls."""

import time
import functools
from typing import Callable, Any, Tuple, Type, Optional
from openai import RateLimitError, APIError, APIConnectionError, Timeout
from slack_sdk.errors import SlackApiError
from src.utils import setup_logging

logger = setup_logging()


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


# Default configurations for different services
OPENAI_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0
)

GITHUB_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=10.0,  # GitHub has stricter limits
    max_delay=120.0,
    exponential_base=2.0
)

SLACK_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0
)

FAISS_RETRY_CONFIG = RetryConfig(
    max_retries=2,
    initial_delay=0.5,
    max_delay=5.0,
    exponential_base=2.0
)


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay with exponential backoff.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        
    Returns:
        Delay in seconds
    """
    delay = config.initial_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)
    
    # Add jitter to prevent thundering herd
    if config.jitter:
        import random
        delay = delay * (0.5 + random.random())
    
    return delay


def retry_on_error(
    config: RetryConfig = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for retrying functions on specific exceptions.
    
    Args:
        config: Retry configuration (default: OPENAI_RETRY_CONFIG)
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback function called on each retry
        
    Returns:
        Decorated function
    """
    if config is None:
        config = OPENAI_RETRY_CONFIG
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < config.max_retries - 1:
                        delay = calculate_delay(attempt, config)
                        
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{config.max_retries}): "
                            f"{type(e).__name__}: {str(e)[:100]}. Retrying in {delay:.1f}s..."
                        )
                        
                        # Call retry callback if provided
                        if on_retry:
                            on_retry(e, attempt)
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {config.max_retries} attempts: "
                            f"{type(e).__name__}: {str(e)[:100]}"
                        )
            
            # All retries exhausted, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator


class OpenAIRetryHandler:
    """Specialized retry handler for OpenAI API calls."""
    
    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """Check if an error is retryable."""
        return isinstance(error, (
            RateLimitError,
            APIConnectionError,
            Timeout,
            APIError
        ))
    
    @staticmethod
    def get_retry_config(error: Exception) -> RetryConfig:
        """Get appropriate retry config based on error type."""
        if isinstance(error, RateLimitError):
            return GITHUB_RETRY_CONFIG  # Use longer delays for rate limits
        return OPENAI_RETRY_CONFIG
    
    @staticmethod
    def retry_with_fallback(
        func: Callable,
        fallback_value: Any = None,
        on_final_failure: Optional[Callable[[Exception], Any]] = None
    ) -> Any:
        """
        Retry a function with fallback value on complete failure.
        
        Args:
            func: Function to call
            fallback_value: Value to return if all retries fail
            on_final_failure: Callback function on final failure
            
        Returns:
            Function result or fallback value
        """
        try:
            return func()
        except Exception as e:
            logger.error(f"All retries failed: {e}")
            
            if on_final_failure:
                return on_final_failure(e)
            
            return fallback_value


class SlackRetryHandler:
    """Specialized retry handler for Slack API calls."""
    
    @staticmethod
    def is_retryable(error: SlackApiError) -> bool:
        """Check if a Slack error is retryable."""
        # Retryable Slack errors
        retryable_errors = {
            'rate_limited',
            'internal_error',
            'fatal_error',
            'service_unavailable',
        }
        
        error_type = error.response.get('error', '')
        return error_type in retryable_errors
    
    @staticmethod
    def get_retry_after(error: SlackApiError) -> Optional[float]:
        """Extract Retry-After header from Slack error."""
        if error.response.get('error') == 'rate_limited':
            # Slack provides retry_after in the response
            return float(error.response.get('retry_after', 1))
        return None
    
    @staticmethod
    @retry_on_error(
        config=SLACK_RETRY_CONFIG,
        exceptions=(SlackApiError,)
    )
    def safe_api_call(func: Callable, *args, **kwargs) -> Any:
        """
        Safely call Slack API with retry logic.
        
        Args:
            func: Slack API function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            API response
        """
        try:
            return func(*args, **kwargs)
        except SlackApiError as e:
            if not SlackRetryHandler.is_retryable(e):
                logger.error(f"Non-retryable Slack error: {e.response['error']}")
                raise
            
            # Handle rate limiting with Retry-After header
            retry_after = SlackRetryHandler.get_retry_after(e)
            if retry_after:
                logger.warning(f"Slack rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
            
            raise  # Re-raise for retry decorator


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascade failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type to monitor
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker.
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open
        """
        if self.state == 'open':
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = 'half_open'
                logger.info("Circuit breaker entering half-open state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset or close circuit
            if self.state == 'half_open':
                self.state = 'closed'
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'open'
                logger.error(
                    f"Circuit breaker OPENED after {self.failure_count} failures"
                )
            
            raise


def with_timeout(timeout_seconds: float):
    """
    Decorator to add timeout to functions.
    
    Args:
        timeout_seconds: Maximum execution time
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"{func.__name__} exceeded {timeout_seconds}s timeout")
            
            # Set timeout alarm (Unix only)
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout_seconds))
                
                try:
                    result = func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                
                return result
                
            except AttributeError:
                # Windows doesn't support SIGALRM, just run normally
                logger.warning("Timeout not supported on this platform")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Convenience functions for common use cases

def safe_openai_call(func: Callable, fallback: str = None) -> Any:
    """
    Safely call OpenAI API with retry and fallback.
    
    Args:
        func: Function that calls OpenAI API
        fallback: Fallback string if all retries fail
        
    Returns:
        API response or fallback
    """
    @retry_on_error(
        config=GITHUB_RETRY_CONFIG,
        exceptions=(RateLimitError, APIError, APIConnectionError, Timeout)
    )
    def _call():
        return func()
    
    try:
        return _call()
    except Exception as e:
        logger.error(f"OpenAI call failed: {e}")
        if fallback:
            return fallback
        raise


def safe_slack_call(func: Callable, *args, **kwargs) -> Any:
    """
    Safely call Slack API with retry.
    
    Args:
        func: Slack API function
        *args, **kwargs: Function arguments
        
    Returns:
        API response
    """
    return SlackRetryHandler.safe_api_call(func, *args, **kwargs)


def safe_file_operation(func: Callable, fallback: Any = None) -> Any:
    """
    Safely perform file operation with retry.
    
    Args:
        func: File operation function
        fallback: Fallback value on failure
        
    Returns:
        Operation result or fallback
    """
    @retry_on_error(
        config=FAISS_RETRY_CONFIG,
        exceptions=(IOError, OSError, PermissionError)
    )
    def _call():
        return func()
    
    try:
        return _call()
    except Exception as e:
        logger.error(f"File operation failed: {e}")
        if fallback is not None:
            return fallback
        raise
