"""
Data models for messaging abstraction layer.

Defines all request/response models used across the messaging adapter interface.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class MessageFormat(str, Enum):
    """Supported message formats."""

    JSON = "json"
    AVRO = "avro"
    PROTOBUF = "protobuf"
    STRING = "string"
    BYTES = "bytes"


@dataclass
class TopicPartition:
    """Information about a topic partition."""

    partition_id: int
    leader: int
    replicas: List[int]
    isr: List[int]  # In-sync replicas


@dataclass
class TopicInfo:
    """Basic information about a Kafka topic."""

    name: str
    partition_count: int
    replication_factor: int
    is_internal: bool = False
    config: Dict[str, str] = field(default_factory=dict)


@dataclass
class TopicMetadata:
    """Detailed metadata about a Kafka topic."""

    name: str
    partitions: List[TopicPartition]
    replication_factor: int
    message_count: int
    size_bytes: int
    created_at: Optional[datetime] = None
    config: Dict[str, str] = field(default_factory=dict)

    @property
    def partition_count(self) -> int:
        """Get the number of partitions."""
        return len(self.partitions)


@dataclass
class RawMessage:
    """A raw message from Kafka."""

    key: Optional[bytes]
    value: bytes
    partition: int
    offset: int
    timestamp: int
    timestamp_type: int  # 0=CreateTime, 1=LogAppendTime
    headers: Dict[str, bytes] = field(default_factory=dict)
    checksum: Optional[int] = None
    serialized_key_size: int = 0
    serialized_value_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "partition": self.partition,
            "offset": self.offset,
            "timestamp": self.timestamp,
            "timestamp_type": self.timestamp_type,
            "headers": self.headers,
            "checksum": self.checksum,
            "serialized_key_size": self.serialized_key_size,
            "serialized_value_size": self.serialized_value_size,
        }


@dataclass
class ProduceMessage:
    """A message to produce to Kafka."""

    value: bytes
    key: Optional[bytes] = None
    headers: Dict[str, bytes] = field(default_factory=dict)
    partition: Optional[int] = None
    timestamp: Optional[int] = None


@dataclass
class ProduceResult:
    """Result of producing messages to Kafka."""

    topic: str
    partition: int
    offset: int
    timestamp: int
    produced_count: int
    failed_count: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        """Check if all messages were produced successfully."""
        return self.failed_count == 0


@dataclass
class LagInfo:
    """Consumer group lag information."""

    group_id: str
    topic: str
    partition: int
    current_offset: int
    log_end_offset: int
    lag: int

    @property
    def is_caught_up(self) -> bool:
        """Check if consumer is caught up."""
        return self.lag == 0


@dataclass
class OffsetRange:
    """Range of offsets for a partition."""

    partition: int
    earliest_offset: int
    latest_offset: int

    @property
    def message_count(self) -> int:
        """Get the number of messages in this range."""
        return max(0, self.latest_offset - self.earliest_offset)


@dataclass
class ConsumerGroupInfo:
    """Information about a consumer group."""

    group_id: str
    state: str  # Stable, Rebalancing, Empty, Dead
    protocol_type: str
    members: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)


@dataclass
class BrokerInfo:
    """Information about a Kafka broker."""

    broker_id: int
    host: str
    port: int
    rack: Optional[str] = None

    @property
    def address(self) -> str:
        """Get the broker address."""
        return f"{self.host}:{self.port}"


@dataclass
class ClusterMetadata:
    """Metadata about the Kafka cluster."""

    brokers: List[BrokerInfo]
    controller_id: int
    cluster_id: Optional[str] = None

    @property
    def broker_count(self) -> int:
        """Get the number of brokers."""
        return len(self.brokers)
