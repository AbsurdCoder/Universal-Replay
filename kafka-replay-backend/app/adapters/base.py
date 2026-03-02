"""
Abstract base class for messaging adapters.

Defines the interface that all messaging implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional
import structlog

from .models import (
    TopicInfo,
    TopicMetadata,
    RawMessage,
    ProduceMessage,
    ProduceResult,
    LagInfo,
    ConsumerGroupInfo,
    ClusterMetadata,
)
from .exceptions import MessagingAdapterError

logger = structlog.get_logger(__name__)


class BaseMessagingAdapter(ABC):
    """
    Abstract base class for messaging adapters.

    Defines the interface for interacting with message brokers.
    All methods are async to support non-blocking I/O operations.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Connect to the message broker.

        Raises:
            MessagingAdapterError: If connection fails.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from the message broker.

        Gracefully closes all connections and resources.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the adapter is healthy and connected.

        Returns:
            True if healthy, False otherwise.
        """
        pass

    # Topic operations

    @abstractmethod
    async def list_topics(self) -> List[TopicInfo]:
        """
        List all topics in the broker.

        Returns:
            List of TopicInfo objects.

        Raises:
            MessagingAdapterError: If operation fails.
        """
        pass

    @abstractmethod
    async def get_topic_metadata(self, topic: str) -> TopicMetadata:
        """
        Get detailed metadata about a topic.

        Args:
            topic: Topic name.

        Returns:
            TopicMetadata object with detailed information.

        Raises:
            TopicNotFoundError: If topic does not exist.
            MessagingAdapterError: If operation fails.
        """
        pass

    @abstractmethod
    async def create_topic(
        self,
        topic: str,
        num_partitions: int = 1,
        replication_factor: int = 1,
        config: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Create a new topic.

        Args:
            topic: Topic name.
            num_partitions: Number of partitions.
            replication_factor: Replication factor.
            config: Optional topic configuration.

        Raises:
            MessagingAdapterError: If operation fails.
        """
        pass

    @abstractmethod
    async def delete_topic(self, topic: str) -> None:
        """
        Delete a topic.

        Args:
            topic: Topic name.

        Raises:
            TopicNotFoundError: If topic does not exist.
            MessagingAdapterError: If operation fails.
        """
        pass

    # Message consumption

    @abstractmethod
    async def consume_messages(
        self,
        topic: str,
        partition: int,
        offset_start: int,
        offset_end: int,
        max_messages: Optional[int] = None,
    ) -> AsyncGenerator[RawMessage, None]:
        """
        Consume messages from a topic partition.

        This is an async generator that yields messages one at a time.
        Messages are NOT buffered in memory - they are fetched and yielded
        as they arrive from the broker.

        Args:
            topic: Topic name.
            partition: Partition number.
            offset_start: Starting offset (inclusive).
            offset_end: Ending offset (exclusive).
            max_messages: Maximum number of messages to consume (optional).

        Yields:
            RawMessage objects.

        Raises:
            TopicNotFoundError: If topic does not exist.
            PartitionNotFoundError: If partition does not exist.
            OffsetOutOfRangeError: If offsets are out of range.
            MessagingAdapterError: If operation fails.
        """
        pass

    # Message production

    @abstractmethod
    async def produce_messages(
        self,
        topic: str,
        messages: List[ProduceMessage],
        headers: Optional[Dict[str, bytes]] = None,
        replay_job_id: Optional[str] = None,
    ) -> ProduceResult:
        """
        Produce messages to a topic.

        Automatically injects replay trace headers if replay_job_id is provided:
        - x-replay-source-offset: Original message offset
        - x-replay-timestamp: Replay timestamp
        - x-replay-job-id: Replay job ID

        Args:
            topic: Topic name.
            messages: List of ProduceMessage objects.
            headers: Optional headers to add to all messages.
            replay_job_id: Optional replay job ID for tracing.

        Returns:
            ProduceResult with information about produced messages.

        Raises:
            TopicNotFoundError: If topic does not exist.
            ProduceError: If production fails.
            MessagingAdapterError: If operation fails.
        """
        pass

    # Consumer group operations

    @abstractmethod
    async def get_consumer_group_lag(self, group_id: str) -> List[LagInfo]:
        """
        Get consumer group lag information.

        Returns lag information for all topic partitions in the group.

        Args:
            group_id: Consumer group ID.

        Returns:
            List of LagInfo objects.

        Raises:
            ConsumerGroupError: If group does not exist or operation fails.
            MessagingAdapterError: If operation fails.
        """
        pass

    @abstractmethod
    async def get_consumer_group_info(self, group_id: str) -> ConsumerGroupInfo:
        """
        Get information about a consumer group.

        Args:
            group_id: Consumer group ID.

        Returns:
            ConsumerGroupInfo object.

        Raises:
            ConsumerGroupError: If group does not exist or operation fails.
            MessagingAdapterError: If operation fails.
        """
        pass

    @abstractmethod
    async def reset_consumer_group_offset(
        self,
        group_id: str,
        topic: str,
        partition: int,
        offset: int,
    ) -> None:
        """
        Reset consumer group offset for a partition.

        Args:
            group_id: Consumer group ID.
            topic: Topic name.
            partition: Partition number.
            offset: Target offset.

        Raises:
            MessagingAdapterError: If operation fails.
        """
        pass

    # Cluster operations

    @abstractmethod
    async def get_cluster_metadata(self) -> ClusterMetadata:
        """
        Get cluster metadata.

        Returns:
            ClusterMetadata object.

        Raises:
            MessagingAdapterError: If operation fails.
        """
        pass

    # Offset operations

    @abstractmethod
    async def get_partition_offsets(
        self,
        topic: str,
        partition: int,
    ) -> tuple[int, int]:
        """
        Get earliest and latest offsets for a partition.

        Args:
            topic: Topic name.
            partition: Partition number.

        Returns:
            Tuple of (earliest_offset, latest_offset).

        Raises:
            TopicNotFoundError: If topic does not exist.
            PartitionNotFoundError: If partition does not exist.
            MessagingAdapterError: If operation fails.
        """
        pass

    @abstractmethod
    async def get_message_count(
        self,
        topic: str,
        partition: int,
    ) -> int:
        """
        Get the number of messages in a partition.

        Args:
            topic: Topic name.
            partition: Partition number.

        Returns:
            Number of messages.

        Raises:
            TopicNotFoundError: If topic does not exist.
            PartitionNotFoundError: If partition does not exist.
            MessagingAdapterError: If operation fails.
        """
        pass

    # Context manager support

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
