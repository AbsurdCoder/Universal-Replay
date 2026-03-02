"""
Exceptions for messaging abstraction layer.

Defines all custom exceptions used across the messaging adapter interface.
"""

from typing import Optional


class MessagingAdapterError(Exception):
    """Base exception for all messaging adapter errors."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class KafkaBrokerError(MessagingAdapterError):
    """Raised when Kafka broker is unavailable or unreachable."""

    def __init__(
        self,
        message: str,
        brokers: Optional[list[str]] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message, "KAFKA_BROKER_ERROR")
        self.brokers = brokers or []
        self.retry_after = retry_after


class TopicNotFoundError(MessagingAdapterError):
    """Raised when a topic is not found."""

    def __init__(self, topic: str):
        super().__init__(f"Topic '{topic}' not found", "TOPIC_NOT_FOUND")
        self.topic = topic


class PartitionNotFoundError(MessagingAdapterError):
    """Raised when a partition is not found."""

    def __init__(self, topic: str, partition: int):
        super().__init__(
            f"Partition {partition} not found for topic '{topic}'",
            "PARTITION_NOT_FOUND",
        )
        self.topic = topic
        self.partition = partition


class OffsetOutOfRangeError(MessagingAdapterError):
    """Raised when an offset is out of range."""

    def __init__(self, topic: str, partition: int, offset: int, valid_range: tuple):
        super().__init__(
            f"Offset {offset} out of range [{valid_range[0]}, {valid_range[1]}) "
            f"for partition {partition} in topic '{topic}'",
            "OFFSET_OUT_OF_RANGE",
        )
        self.topic = topic
        self.partition = partition
        self.offset = offset
        self.valid_range = valid_range


class ProduceError(MessagingAdapterError):
    """Raised when message production fails."""

    def __init__(
        self,
        message: str,
        topic: Optional[str] = None,
        failed_count: int = 0,
        errors: Optional[list[str]] = None,
    ):
        super().__init__(message, "PRODUCE_ERROR")
        self.topic = topic
        self.failed_count = failed_count
        self.errors = errors or []


class ConsumerGroupError(MessagingAdapterError):
    """Raised when consumer group operation fails."""

    def __init__(self, group_id: str, message: str):
        super().__init__(
            f"Consumer group '{group_id}' error: {message}",
            "CONSUMER_GROUP_ERROR",
        )
        self.group_id = group_id


class SerializationError(MessagingAdapterError):
    """Raised when message serialization/deserialization fails."""

    def __init__(self, message: str, format_type: Optional[str] = None):
        super().__init__(message, "SERIALIZATION_ERROR")
        self.format_type = format_type


class TimeoutError(MessagingAdapterError):
    """Raised when an operation times out."""

    def __init__(self, message: str, timeout_seconds: Optional[float] = None):
        super().__init__(message, "TIMEOUT_ERROR")
        self.timeout_seconds = timeout_seconds


class ConfigurationError(MessagingAdapterError):
    """Raised when adapter configuration is invalid."""

    def __init__(self, message: str):
        super().__init__(message, "CONFIGURATION_ERROR")


class ConnectionError(MessagingAdapterError):
    """Raised when connection to Kafka fails."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, "CONNECTION_ERROR")
        self.retry_after = retry_after
