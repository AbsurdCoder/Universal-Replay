"""
Error handling utilities for messaging adapter.

Provides utilities for handling, logging, and recovering from messaging errors.
"""

from typing import Callable, TypeVar, Optional, Any
import asyncio
import structlog
from functools import wraps
from datetime import datetime, timedelta

from .exceptions import (
    MessagingAdapterError,
    KafkaBrokerError,
    ConnectionError as AdapterConnectionError,
    TimeoutError as AdapterTimeoutError,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts.
            initial_delay: Initial delay between retries in seconds.
            max_delay: Maximum delay between retries in seconds.
            exponential_base: Base for exponential backoff.
            jitter: Whether to add random jitter to delays.
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.

        Args:
            attempt: Attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random

            delay = delay * (0.5 + random.random())

        return delay


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by stopping requests when a service is unhealthy.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit.
            recovery_timeout: Seconds to wait before attempting recovery.
            expected_exception: Exception type to catch.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Function result.

        Raises:
            MessagingAdapterError: If circuit is open.
            Exception: If function fails.
        """
        if self.state == "open":
            if self._should_attempt_recovery():
                self.state = "half-open"
                logger.info("circuit_breaker_attempting_recovery")
            else:
                raise MessagingAdapterError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute async function through circuit breaker.

        Args:
            func: Async function to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Function result.

        Raises:
            MessagingAdapterError: If circuit is open.
            Exception: If function fails.
        """
        if self.state == "open":
            if self._should_attempt_recovery():
                self.state = "half-open"
                logger.info("circuit_breaker_attempting_recovery")
            else:
                raise MessagingAdapterError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            logger.info("circuit_breaker_closed")
        elif self.state == "closed":
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self.failure_count,
            )

    def _should_attempt_recovery(self) -> bool:
        """Check if circuit should attempt recovery."""
        if not self.last_failure_time:
            return True

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = None
        logger.info("circuit_breaker_reset")


def retry_async(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable] = None,
):
    """
    Decorator for retrying async functions with exponential backoff.

    Args:
        config: RetryConfig instance.
        on_retry: Optional callback called on each retry.

    Example:
        @retry_async(RetryConfig(max_attempts=3))
        async def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    logger.debug(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=config.max_attempts,
                    )
                    return await func(*args, **kwargs)

                except (KafkaBrokerError, AdapterConnectionError, AdapterTimeoutError) as e:
                    last_exception = e

                    if attempt < config.max_attempts - 1:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            "retry_scheduled",
                            function=func.__name__,
                            attempt=attempt + 1,
                            delay=delay,
                            error=str(e),
                        )

                        if on_retry:
                            on_retry(attempt, delay, e)

                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=config.max_attempts,
                            error=str(e),
                        )

                except Exception as e:
                    # Don't retry on non-transient errors
                    logger.error(
                        "non_retryable_error",
                        function=func.__name__,
                        error=str(e),
                    )
                    raise

            if last_exception:
                raise last_exception
            raise RuntimeError(f"Failed to execute {func.__name__}")

        return wrapper

    return decorator


class ErrorRecoveryStrategy:
    """Strategy for recovering from messaging errors."""

    @staticmethod
    def should_retry(error: Exception) -> bool:
        """
        Determine if an error should be retried.

        Args:
            error: Exception to evaluate.

        Returns:
            True if error is transient and should be retried.
        """
        # Transient errors that should be retried
        transient_errors = (
            KafkaBrokerError,
            AdapterConnectionError,
            AdapterTimeoutError,
            asyncio.TimeoutError,
            ConnectionError,
        )

        return isinstance(error, transient_errors)

    @staticmethod
    def get_retry_delay(error: Exception, attempt: int) -> float:
        """
        Get recommended retry delay for an error.

        Args:
            error: Exception to evaluate.
            attempt: Attempt number (0-indexed).

        Returns:
            Recommended delay in seconds.
        """
        # Check if error specifies retry_after
        if hasattr(error, "retry_after") and error.retry_after:
            return float(error.retry_after)

        # Default exponential backoff
        config = RetryConfig()
        return config.get_delay(attempt)

    @staticmethod
    def get_error_context(error: Exception) -> dict:
        """
        Extract context information from an error.

        Args:
            error: Exception to extract context from.

        Returns:
            Dictionary with error context.
        """
        context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        # Add error-specific context
        if isinstance(error, KafkaBrokerError):
            context["brokers"] = error.brokers
            context["retry_after"] = error.retry_after
        elif isinstance(error, MessagingAdapterError):
            context["code"] = error.code

        return context


def handle_messaging_error(error: Exception) -> None:
    """
    Handle a messaging error with appropriate logging.

    Args:
        error: Exception to handle.
    """
    context = ErrorRecoveryStrategy.get_error_context(error)

    if ErrorRecoveryStrategy.should_retry(error):
        logger.warning("transient_error_occurred", **context)
    else:
        logger.error("permanent_error_occurred", **context)
