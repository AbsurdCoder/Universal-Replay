"""
Kafka adapter implementation using aiokafka.

Provides a concrete implementation of the messaging adapter for Apache Kafka.
Includes connection pooling, async generators for memory-efficient streaming,
and replay trace header injection.
"""

import time
from typing import AsyncGenerator, Dict, List, Optional
from datetime import datetime
import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, AIOKafkaAdminClient
from aiokafka.errors import (
    KafkaError,
    TopicAlreadyExistsError,
    UnknownTopicOrPartError,
    OffsetOutOfRangeError as AIOKafkaOffsetOutOfRangeError,
    BrokerConnectionError,
    NoBrokersAvailable,
)

from .base import BaseMessagingAdapter
from .config import KafkaSettings
from .models import (
    TopicInfo,
    TopicMetadata,
    TopicPartition,
    RawMessage,
    ProduceMessage,
    ProduceResult,
    LagInfo,
    ConsumerGroupInfo,
    ClusterMetadata,
    BrokerInfo,
)
from .exceptions import (
    KafkaBrokerError,
    TopicNotFoundError,
    PartitionNotFoundError,
    OffsetOutOfRangeError,
    ProduceError,
    ConsumerGroupError,
    ConnectionError as AdapterConnectionError,
    MessagingAdapterError,
)

logger = structlog.get_logger(__name__)


class KafkaAdapter(BaseMessagingAdapter):
    """
    Kafka adapter implementation using aiokafka.

    Features:
    - Connection pooling with reusable admin/consumer/producer clients
    - Memory-efficient message streaming with async generators
    - Automatic replay trace header injection
    - Comprehensive error handling with typed exceptions
    - Graceful broker unavailability handling
    """

    def __init__(self, settings: KafkaSettings):
        """
        Initialize Kafka adapter.

        Args:
            settings: KafkaSettings instance with configuration.
        """
        self.settings = settings
        self.admin_client: Optional[AIOKafkaAdminClient] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self._connected = False

    async def connect(self) -> None:
        """
        Connect to Kafka broker.

        Creates and initializes admin client, consumer, and producer.

        Raises:
            KafkaBrokerError: If connection to broker fails.
            AdapterConnectionError: If connection setup fails.
        """
        try:
            logger.info(
                "connecting_to_kafka",
                brokers=self.settings.bootstrap_servers,
            )

            # Initialize admin client for metadata operations
            self.admin_client = AIOKafkaAdminClient(
                bootstrap_servers=self.settings.get_bootstrap_servers_list(),
                client_id=self.settings.client_id,
                request_timeout_ms=self.settings.request_timeout_ms,
                connections_max_idle_ms=self.settings.connections_max_idle_ms,
                security_protocol=self.settings.security_protocol,
                **self.settings.get_sasl_config(),
                **self.settings.get_ssl_config(),
            )

            await self.admin_client.start()

            # Initialize producer for message production
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.settings.get_bootstrap_servers_list(),
                client_id=f"{self.settings.client_id}-producer",
                acks=self.settings.acks,
                retries=self.settings.retries,
                retry_backoff_ms=self.settings.retry_backoff_ms,
                batch_size=self.settings.batch_size,
                linger_ms=self.settings.linger_ms,
                compression_type=self.settings.compression_type,
                request_timeout_ms=self.settings.request_timeout_ms,
                connections_max_idle_ms=self.settings.connections_max_idle_ms,
                security_protocol=self.settings.security_protocol,
                **self.settings.get_sasl_config(),
                **self.settings.get_ssl_config(),
            )

            await self.producer.start()

            self._connected = True
            logger.info("kafka_connected", brokers=self.settings.bootstrap_servers)

        except (BrokerConnectionError, NoBrokersAvailable) as e:
            logger.error(
                "kafka_broker_connection_failed",
                error=str(e),
                brokers=self.settings.bootstrap_servers,
            )
            raise KafkaBrokerError(
                f"Failed to connect to Kafka brokers: {str(e)}",
                brokers=self.settings.get_bootstrap_servers_list(),
                retry_after=5,
            )
        except Exception as e:
            logger.error("kafka_connection_failed", error=str(e))
            raise AdapterConnectionError(f"Failed to connect to Kafka: {str(e)}")

    async def disconnect(self) -> None:
        """
        Disconnect from Kafka broker.

        Gracefully closes all connections and resources.
        """
        try:
            logger.info("disconnecting_from_kafka")

            if self.producer:
                await self.producer.stop()
            if self.consumer:
                await self.consumer.stop()
            if self.admin_client:
                await self.admin_client.close()

            self._connected = False
            logger.info("kafka_disconnected")

        except Exception as e:
            logger.error("kafka_disconnect_error", error=str(e))

    async def health_check(self) -> bool:
        """
        Check if adapter is healthy and connected.

        Returns:
            True if connected and healthy, False otherwise.
        """
        if not self._connected or not self.admin_client:
            return False

        try:
            await self.admin_client.describe_cluster()
            return True
        except Exception as e:
            logger.warning("health_check_failed", error=str(e))
            return False

    # Topic operations

    async def list_topics(self) -> List[TopicInfo]:
        """
        List all topics in the cluster.

        Returns:
            List of TopicInfo objects.

        Raises:
            KafkaBrokerError: If broker is unavailable.
            MessagingAdapterError: If operation fails.
        """
        if not self.admin_client:
            raise AdapterConnectionError("Not connected to Kafka")

        try:
            metadata = await self.admin_client.describe_cluster()
            topics_metadata = await self.admin_client.fetch_all_metadata()

            topics = []
            for topic_partition in topics_metadata.topics():
                topic_name = topic_partition.topic
                partitions = topics_metadata.partitions(topic_name)

                if partitions:
                    first_partition = partitions[0]
                    replication_factor = len(
                        topics_metadata.replicas(topic_name, first_partition)
                    )

                    topics.append(
                        TopicInfo(
                            name=topic_name,
                            partition_count=len(partitions),
                            replication_factor=replication_factor,
                        )
                    )

            logger.info("topics_listed", count=len(topics))
            return topics

        except (BrokerConnectionError, NoBrokersAvailable) as e:
            logger.error("list_topics_broker_error", error=str(e))
            raise KafkaBrokerError(
                f"Broker unavailable: {str(e)}",
                brokers=self.settings.get_bootstrap_servers_list(),
            )
        except Exception as e:
            logger.error("list_topics_error", error=str(e))
            raise MessagingAdapterError(f"Failed to list topics: {str(e)}")

    async def get_topic_metadata(self, topic: str) -> TopicMetadata:
        """
        Get detailed metadata about a topic.

        Args:
            topic: Topic name.

        Returns:
            TopicMetadata object.

        Raises:
            TopicNotFoundError: If topic does not exist.
            KafkaBrokerError: If broker is unavailable.
            MessagingAdapterError: If operation fails.
        """
        if not self.admin_client:
            raise AdapterConnectionError("Not connected to Kafka")

        try:
            topics_metadata = await self.admin_client.fetch_all_metadata(topics=[topic])

            if not topics_metadata.topics():
                raise TopicNotFoundError(topic)

            partitions_list = []
            total_messages = 0
            total_size = 0

            for partition_id in topics_metadata.partitions(topic):
                leader = topics_metadata.leader(topic, partition_id)
                replicas = topics_metadata.replicas(topic, partition_id)
                isr = topics_metadata.isr(topic, partition_id)

                partitions_list.append(
                    TopicPartition(
                        partition_id=partition_id,
                        leader=leader,
                        replicas=list(replicas),
                        isr=list(isr),
                    )
                )

                # Get message count for this partition
                try:
                    earliest, latest = await self.get_partition_offsets(topic, partition_id)
                    total_messages += max(0, latest - earliest)
                except Exception as e:
                    logger.warning(
                        "get_partition_offsets_error",
                        topic=topic,
                        partition=partition_id,
                        error=str(e),
                    )

            replication_factor = len(
                topics_metadata.replicas(topic, topics_metadata.partitions(topic)[0])
            )

            metadata = TopicMetadata(
                name=topic,
                partitions=partitions_list,
                replication_factor=replication_factor,
                message_count=total_messages,
                size_bytes=total_size,
            )

            logger.info(
                "topic_metadata_retrieved",
                topic=topic,
                partitions=len(partitions_list),
            )
            return metadata

        except TopicNotFoundError:
            raise
        except (BrokerConnectionError, NoBrokersAvailable) as e:
            logger.error("get_topic_metadata_broker_error", topic=topic, error=str(e))
            raise KafkaBrokerError(f"Broker unavailable: {str(e)}")
        except Exception as e:
            logger.error("get_topic_metadata_error", topic=topic, error=str(e))
            raise MessagingAdapterError(
                f"Failed to get metadata for topic '{topic}': {str(e)}"
            )

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
        if not self.admin_client:
            raise AdapterConnectionError("Not connected to Kafka")

        try:
            from aiokafka.admin import NewTopic

            new_topic = NewTopic(
                name=topic,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                topic_configs=config or {},
            )

            await self.admin_client.create_topics([new_topic])
            logger.info(
                "topic_created",
                topic=topic,
                partitions=num_partitions,
                replication_factor=replication_factor,
            )

        except TopicAlreadyExistsError:
            logger.warning("topic_already_exists", topic=topic)
        except Exception as e:
            logger.error("create_topic_error", topic=topic, error=str(e))
            raise MessagingAdapterError(f"Failed to create topic '{topic}': {str(e)}")

    async def delete_topic(self, topic: str) -> None:
        """
        Delete a topic.

        Args:
            topic: Topic name.

        Raises:
            TopicNotFoundError: If topic does not exist.
            MessagingAdapterError: If operation fails.
        """
        if not self.admin_client:
            raise AdapterConnectionError("Not connected to Kafka")

        try:
            await self.admin_client.delete_topics([topic])
            logger.info("topic_deleted", topic=topic)

        except UnknownTopicOrPartError:
            raise TopicNotFoundError(topic)
        except Exception as e:
            logger.error("delete_topic_error", topic=topic, error=str(e))
            raise MessagingAdapterError(f"Failed to delete topic '{topic}': {str(e)}")

    # Message consumption

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

        This async generator yields messages one at a time without buffering.
        Memory-efficient for large message sets.

        Args:
            topic: Topic name.
            partition: Partition number.
            offset_start: Starting offset (inclusive).
            offset_end: Ending offset (exclusive).
            max_messages: Maximum messages to consume.

        Yields:
            RawMessage objects.

        Raises:
            TopicNotFoundError: If topic does not exist.
            PartitionNotFoundError: If partition does not exist.
            OffsetOutOfRangeError: If offsets are out of range.
            KafkaBrokerError: If broker is unavailable.
        """
        consumer = None
        try:
            # Validate partition exists
            try:
                await self.get_topic_metadata(topic)
            except TopicNotFoundError:
                raise
            except Exception as e:
                raise MessagingAdapterError(f"Failed to validate topic: {str(e)}")

            # Validate offsets
            earliest, latest = await self.get_partition_offsets(topic, partition)
            if offset_start < earliest or offset_start >= latest:
                raise OffsetOutOfRangeError(
                    topic, partition, offset_start, (earliest, latest)
                )
            if offset_end < earliest or offset_end > latest:
                raise OffsetOutOfRangeError(
                    topic, partition, offset_end, (earliest, latest)
                )

            # Create consumer for this partition
            consumer = AIOKafkaConsumer(
                bootstrap_servers=self.settings.get_bootstrap_servers_list(),
                client_id=f"{self.settings.client_id}-consumer",
                group_id=None,  # Don't use consumer group
                auto_offset_reset="none",
                enable_auto_commit=False,
                request_timeout_ms=self.settings.request_timeout_ms,
                connections_max_idle_ms=self.settings.connections_max_idle_ms,
                security_protocol=self.settings.security_protocol,
                **self.settings.get_sasl_config(),
                **self.settings.get_ssl_config(),
            )

            await consumer.start()
            consumer.assign([(topic, partition)])
            consumer.seek(topic, partition, offset_start)

            messages_consumed = 0

            async for msg in consumer:
                if msg.offset >= offset_end:
                    break

                if max_messages and messages_consumed >= max_messages:
                    break

                # Convert aiokafka message to RawMessage
                headers_dict = {}
                if msg.headers:
                    for key, value in msg.headers:
                        headers_dict[key.decode() if isinstance(key, bytes) else key] = (
                            value
                        )

                raw_message = RawMessage(
                    key=msg.key,
                    value=msg.value,
                    partition=msg.partition,
                    offset=msg.offset,
                    timestamp=msg.timestamp,
                    timestamp_type=msg.timestamp_type,
                    headers=headers_dict,
                    checksum=msg.checksum,
                    serialized_key_size=msg.serialized_key_size,
                    serialized_value_size=msg.serialized_value_size,
                )

                yield raw_message
                messages_consumed += 1

            logger.info(
                "messages_consumed",
                topic=topic,
                partition=partition,
                count=messages_consumed,
            )

        except (TopicNotFoundError, PartitionNotFoundError, OffsetOutOfRangeError):
            raise
        except (BrokerConnectionError, NoBrokersAvailable) as e:
            logger.error("consume_messages_broker_error", topic=topic, error=str(e))
            raise KafkaBrokerError(f"Broker unavailable: {str(e)}")
        except Exception as e:
            logger.error(
                "consume_messages_error",
                topic=topic,
                partition=partition,
                error=str(e),
            )
            raise MessagingAdapterError(
                f"Failed to consume messages from {topic}[{partition}]: {str(e)}"
            )
        finally:
            if consumer:
                await consumer.stop()

    # Message production

    async def produce_messages(
        self,
        topic: str,
        messages: List[ProduceMessage],
        headers: Optional[Dict[str, bytes]] = None,
        replay_job_id: Optional[str] = None,
    ) -> ProduceResult:
        """
        Produce messages to a topic.

        Automatically injects replay trace headers if replay_job_id is provided.

        Args:
            topic: Topic name.
            messages: List of ProduceMessage objects.
            headers: Optional headers to add to all messages.
            replay_job_id: Optional replay job ID for tracing.

        Returns:
            ProduceResult with production statistics.

        Raises:
            TopicNotFoundError: If topic does not exist.
            ProduceError: If production fails.
            KafkaBrokerError: If broker is unavailable.
        """
        if not self.producer:
            raise AdapterConnectionError("Not connected to Kafka")

        try:
            produced_count = 0
            failed_count = 0
            errors = []
            first_offset = None
            first_partition = None

            for msg in messages:
                try:
                    # Prepare headers
                    msg_headers = dict(msg.headers or {})
                    if headers:
                        msg_headers.update(headers)

                    # Inject replay trace headers
                    if (
                        replay_job_id
                        and self.settings.replay_trace_headers_enabled
                    ):
                        msg_headers[
                            self.settings.replay_source_offset_header
                        ] = str(msg.offset or 0).encode()
                        msg_headers[
                            self.settings.replay_timestamp_header
                        ] = str(int(time.time() * 1000)).encode()
                        msg_headers[
                            self.settings.replay_job_id_header
                        ] = replay_job_id.encode()

                    # Convert headers to list of tuples
                    headers_list = [
                        (k, v if isinstance(v, bytes) else v.encode())
                        for k, v in msg_headers.items()
                    ]

                    # Produce message
                    record_metadata = await self.producer.send_and_wait(
                        topic,
                        value=msg.value,
                        key=msg.key,
                        headers=headers_list,
                        partition=msg.partition,
                        timestamp_ms=msg.timestamp,
                    )

                    if first_offset is None:
                        first_offset = record_metadata.offset
                        first_partition = record_metadata.partition

                    produced_count += 1

                except Exception as e:
                    logger.error("produce_message_error", error=str(e))
                    failed_count += 1
                    errors.append(str(e))

            result = ProduceResult(
                topic=topic,
                partition=first_partition or 0,
                offset=first_offset or 0,
                timestamp=int(time.time() * 1000),
                produced_count=produced_count,
                failed_count=failed_count,
                errors=errors,
            )

            logger.info(
                "messages_produced",
                topic=topic,
                count=produced_count,
                failed=failed_count,
            )

            if failed_count > 0:
                raise ProduceError(
                    f"Failed to produce {failed_count} out of {len(messages)} messages",
                    topic=topic,
                    failed_count=failed_count,
                    errors=errors,
                )

            return result

        except ProduceError:
            raise
        except (BrokerConnectionError, NoBrokersAvailable) as e:
            logger.error("produce_messages_broker_error", topic=topic, error=str(e))
            raise KafkaBrokerError(f"Broker unavailable: {str(e)}")
        except Exception as e:
            logger.error("produce_messages_error", topic=topic, error=str(e))
            raise MessagingAdapterError(
                f"Failed to produce messages to topic '{topic}': {str(e)}"
            )

    # Consumer group operations

    async def get_consumer_group_lag(self, group_id: str) -> List[LagInfo]:
        """
        Get consumer group lag information.

        Args:
            group_id: Consumer group ID.

        Returns:
            List of LagInfo objects.

        Raises:
            ConsumerGroupError: If group does not exist.
            KafkaBrokerError: If broker is unavailable.
        """
        if not self.admin_client:
            raise AdapterConnectionError("Not connected to Kafka")

        try:
            # Get group description
            group_desc = await self.admin_client.describe_consumer_groups([group_id])

            if not group_desc or group_id not in group_desc:
                raise ConsumerGroupError(group_id, "Group not found")

            lag_info = []

            # Get offsets for the group
            offsets = await self.admin_client.list_consumer_group_offsets(group_id)

            for (topic, partition), offset_and_metadata in offsets.items():
                current_offset = offset_and_metadata.offset

                # Get log end offset
                try:
                    _, latest_offset = await self.get_partition_offsets(
                        topic, partition
                    )
                    lag = max(0, latest_offset - current_offset)

                    lag_info.append(
                        LagInfo(
                            group_id=group_id,
                            topic=topic,
                            partition=partition,
                            current_offset=current_offset,
                            log_end_offset=latest_offset,
                            lag=lag,
                        )
                    )
                except Exception as e:
                    logger.warning(
                        "get_lag_error",
                        group_id=group_id,
                        topic=topic,
                        partition=partition,
                        error=str(e),
                    )

            logger.info("consumer_group_lag_retrieved", group_id=group_id, count=len(lag_info))
            return lag_info

        except ConsumerGroupError:
            raise
        except (BrokerConnectionError, NoBrokersAvailable) as e:
            logger.error("get_consumer_group_lag_broker_error", error=str(e))
            raise KafkaBrokerError(f"Broker unavailable: {str(e)}")
        except Exception as e:
            logger.error("get_consumer_group_lag_error", group_id=group_id, error=str(e))
            raise ConsumerGroupError(group_id, f"Failed to get lag: {str(e)}")

    async def get_consumer_group_info(self, group_id: str) -> ConsumerGroupInfo:
        """
        Get information about a consumer group.

        Args:
            group_id: Consumer group ID.

        Returns:
            ConsumerGroupInfo object.

        Raises:
            ConsumerGroupError: If group does not exist.
            KafkaBrokerError: If broker is unavailable.
        """
        if not self.admin_client:
            raise AdapterConnectionError("Not connected to Kafka")

        try:
            group_desc = await self.admin_client.describe_consumer_groups([group_id])

            if not group_desc or group_id not in group_desc:
                raise ConsumerGroupError(group_id, "Group not found")

            group = group_desc[group_id]

            return ConsumerGroupInfo(
                group_id=group_id,
                state=group.state,
                protocol_type=group.protocol_type,
                members=[m.member_id for m in group.members],
                topics=list(set(tp[0] for tp in (await self.admin_client.list_consumer_group_offsets(group_id)).keys())),
            )

        except ConsumerGroupError:
            raise
        except (BrokerConnectionError, NoBrokersAvailable) as e:
            logger.error("get_consumer_group_info_broker_error", error=str(e))
            raise KafkaBrokerError(f"Broker unavailable: {str(e)}")
        except Exception as e:
            logger.error("get_consumer_group_info_error", group_id=group_id, error=str(e))
            raise ConsumerGroupError(group_id, f"Failed to get info: {str(e)}")

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
            ConsumerGroupError: If operation fails.
            KafkaBrokerError: If broker is unavailable.
        """
        if not self.admin_client:
            raise AdapterConnectionError("Not connected to Kafka")

        try:
            from aiokafka.structs import OffsetAndMetadata

            offsets = {(topic, partition): OffsetAndMetadata(offset, "")}
            await self.admin_client.alter_consumer_group_offsets(group_id, offsets)

            logger.info(
                "consumer_group_offset_reset",
                group_id=group_id,
                topic=topic,
                partition=partition,
                offset=offset,
            )

        except (BrokerConnectionError, NoBrokersAvailable) as e:
            logger.error("reset_offset_broker_error", error=str(e))
            raise KafkaBrokerError(f"Broker unavailable: {str(e)}")
        except Exception as e:
            logger.error("reset_offset_error", group_id=group_id, error=str(e))
            raise ConsumerGroupError(group_id, f"Failed to reset offset: {str(e)}")

    # Cluster operations

    async def get_cluster_metadata(self) -> ClusterMetadata:
        """
        Get cluster metadata.

        Returns:
            ClusterMetadata object.

        Raises:
            KafkaBrokerError: If broker is unavailable.
            MessagingAdapterError: If operation fails.
        """
        if not self.admin_client:
            raise AdapterConnectionError("Not connected to Kafka")

        try:
            cluster_info = await self.admin_client.describe_cluster()

            brokers = [
                BrokerInfo(
                    broker_id=broker.nodeId,
                    host=broker.host,
                    port=broker.port,
                    rack=broker.rack,
                )
                for broker in cluster_info.brokers
            ]

            return ClusterMetadata(
                brokers=brokers,
                controller_id=cluster_info.controller,
                cluster_id=cluster_info.cluster_id,
            )

        except (BrokerConnectionError, NoBrokersAvailable) as e:
            logger.error("get_cluster_metadata_broker_error", error=str(e))
            raise KafkaBrokerError(f"Broker unavailable: {str(e)}")
        except Exception as e:
            logger.error("get_cluster_metadata_error", error=str(e))
            raise MessagingAdapterError(f"Failed to get cluster metadata: {str(e)}")

    # Offset operations

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
            KafkaBrokerError: If broker is unavailable.
        """
        if not self.admin_client:
            raise AdapterConnectionError("Not connected to Kafka")

        try:
            consumer = AIOKafkaConsumer(
                bootstrap_servers=self.settings.get_bootstrap_servers_list(),
                client_id=f"{self.settings.client_id}-offset-checker",
                security_protocol=self.settings.security_protocol,
                **self.settings.get_sasl_config(),
                **self.settings.get_ssl_config(),
            )

            await consumer.start()

            try:
                consumer.assign([(topic, partition)])
                earliest = await consumer.beginning_offsets([(topic, partition)])
                latest = await consumer.end_offsets([(topic, partition)])

                earliest_offset = earliest.get((topic, partition), 0)
                latest_offset = latest.get((topic, partition), 0)

                return earliest_offset, latest_offset

            finally:
                await consumer.stop()

        except UnknownTopicOrPartError as e:
            if "UNKNOWN_TOPIC_OR_PART" in str(e):
                raise TopicNotFoundError(topic)
            raise PartitionNotFoundError(topic, partition)
        except (BrokerConnectionError, NoBrokersAvailable) as e:
            logger.error("get_partition_offsets_broker_error", error=str(e))
            raise KafkaBrokerError(f"Broker unavailable: {str(e)}")
        except Exception as e:
            logger.error(
                "get_partition_offsets_error",
                topic=topic,
                partition=partition,
                error=str(e),
            )
            raise MessagingAdapterError(
                f"Failed to get offsets for {topic}[{partition}]: {str(e)}"
            )

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
            KafkaBrokerError: If broker is unavailable.
        """
        try:
            earliest, latest = await self.get_partition_offsets(topic, partition)
            return max(0, latest - earliest)
        except (TopicNotFoundError, PartitionNotFoundError):
            raise
        except Exception as e:
            logger.error(
                "get_message_count_error",
                topic=topic,
                partition=partition,
                error=str(e),
            )
            raise MessagingAdapterError(
                f"Failed to get message count for {topic}[{partition}]: {str(e)}"
            )
