"""Service for Kafka topic operations."""

from typing import List

from app.adapters import KafkaAdapter
from app.models import TopicMetadataResponse, TopicListResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class TopicService:
    """Service for managing Kafka topics."""

    def __init__(self, kafka_adapter: KafkaAdapter):
        """Initialize topic service."""
        self.kafka = kafka_adapter

    async def list_topics(self) -> TopicListResponse:
        """List all available topics."""
        try:
            topics = await self.kafka.list_topics()
            logger.info("Listed topics", count=len(topics))
            return TopicListResponse(topics=sorted(topics))
        except Exception as e:
            logger.error("Failed to list topics", error=str(e))
            raise

    async def get_topic_metadata(self, topic: str) -> TopicMetadataResponse:
        """Get metadata for a specific topic."""
        try:
            partitions = await self.kafka.get_topic_partitions(topic)
            earliest, latest = await self.kafka.get_topic_offset_range(topic, partition=0)

            logger.info(
                "Got topic metadata",
                topic=topic,
                partitions=partitions,
                earliest=earliest,
                latest=latest,
            )

            return TopicMetadataResponse(
                name=topic,
                partitions=partitions,
                earliest_offset=earliest,
                latest_offset=latest,
            )
        except Exception as e:
            logger.error("Failed to get topic metadata", topic=topic, error=str(e))
            raise
