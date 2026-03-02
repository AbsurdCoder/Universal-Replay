"""
Topic browsing endpoints.

Provides endpoints for listing topics, viewing metadata, and browsing messages.
"""

import structlog
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.adapters.kafka import KafkaAdapter
from app.services.encoding_service import EncodingService
from .schemas import (
    ErrorResponse,
    TopicsListResponse,
    TopicInfo,
    TopicMetadata,
    MessagesListResponse,
    MessageRecord,
    EncodingDetectionResult,
)
from .dependencies import get_kafka_adapter, get_encoding_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get(
    "",
    response_model=TopicsListResponse,
    responses={
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="List all Kafka topics",
    description="Retrieves a list of all available Kafka topics with basic metadata.",
)
async def list_topics(
    kafka: KafkaAdapter = Depends(get_kafka_adapter),
) -> TopicsListResponse:
    """
    List all Kafka topics.

    Returns:
        TopicsListResponse with topic list.

    Raises:
        HTTPException: If Kafka broker is unavailable.
    """
    try:
        logger.info("listing_topics")
        topics = await kafka.list_topics()

        topic_infos = [
            TopicInfo(
                name=topic.name,
                partitions=topic.partitions,
                replication_factor=topic.replication_factor,
                is_internal=topic.is_internal,
            )
            for topic in topics
        ]

        logger.info("topics_listed", count=len(topic_infos))
        return TopicsListResponse(topics=topic_infos, count=len(topic_infos))

    except Exception as e:
        logger.error("list_topics_failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to list topics: {str(e)}",
        )


@router.get(
    "/{topic}/metadata",
    response_model=TopicMetadata,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Get topic metadata",
    description="Retrieves detailed metadata for a specific Kafka topic, including schema information.",
)
async def get_topic_metadata(
    topic: str,
    kafka: KafkaAdapter = Depends(get_kafka_adapter),
) -> TopicMetadata:
    """
    Get metadata for a specific topic.

    Args:
        topic: Topic name.
        kafka: Kafka adapter.

    Returns:
        TopicMetadata with detailed information.

    Raises:
        HTTPException: If topic not found or broker unavailable.
    """
    try:
        logger.info("getting_topic_metadata", topic=topic)
        metadata = await kafka.get_topic_metadata(topic)

        logger.info("topic_metadata_retrieved", topic=topic)
        return TopicMetadata(
            name=metadata.name,
            partitions=metadata.partitions,
            replication_factor=metadata.replication_factor,
            is_internal=metadata.is_internal,
            schema_id=metadata.schema_id,
            schema_subject=metadata.schema_subject,
            schema_version=metadata.schema_version,
            leader_epochs=metadata.leader_epochs or {},
            isr_replicas=metadata.isr_replicas or {},
        )

    except Exception as e:
        logger.error("get_topic_metadata_failed", topic=topic, error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to get topic metadata: {str(e)}",
        )


@router.get(
    "/{topic}/messages",
    response_model=MessagesListResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Browse messages in a topic",
    description="Retrieves a paginated list of messages from a specific topic partition.",
)
async def browse_messages(
    topic: str,
    partition: int = Query(0, description="Partition number"),
    offset_start: int = Query(0, description="Start offset"),
    limit: int = Query(10, ge=1, le=1000, description="Number of messages to retrieve"),
    kafka: KafkaAdapter = Depends(get_kafka_adapter),
    encoding_service: EncodingService = Depends(get_encoding_service),
) -> MessagesListResponse:
    """
    Browse messages in a topic partition.

    Args:
        topic: Topic name.
        partition: Partition number.
        offset_start: Start offset.
        limit: Number of messages to retrieve.
        kafka: Kafka adapter.
        encoding_service: Encoding service.

    Returns:
        MessagesListResponse with paginated messages.

    Raises:
        HTTPException: If topic not found or broker unavailable.
    """
    try:
        logger.info(
            "browsing_messages",
            topic=topic,
            partition=partition,
            offset_start=offset_start,
            limit=limit,
        )

        offset_end = offset_start + limit

        # Consume messages
        messages = []
        async for raw_msg in kafka.consume_messages(
            topic=topic,
            partition=partition,
            offset_start=offset_start,
            offset_end=offset_end,
            max_messages=limit,
        ):
            # Detect encoding
            encoding_result = await encoding_service.detect_encoding(raw_msg.value, topic)

            # Decode for display
            decoded = await encoding_service.decode_for_display(raw_msg.value, encoding_result)

            messages.append(
                MessageRecord(
                    partition=raw_msg.partition,
                    offset=raw_msg.offset,
                    timestamp=raw_msg.timestamp,
                    key=raw_msg.key.decode() if raw_msg.key else None,
                    value=decoded if isinstance(decoded, dict) else {"_raw": str(decoded)},
                    headers={k: v.decode() if isinstance(v, bytes) else v for k, v in (raw_msg.headers or {}).items()},
                    encoding=encoding_result.encoding,
                )
            )

        logger.info("messages_browsed", topic=topic, count=len(messages))
        return MessagesListResponse(
            topic=topic,
            partition=partition,
            messages=messages,
            total_available=limit,
            offset_start=offset_start,
            offset_end=offset_end,
        )

    except Exception as e:
        logger.error(
            "browse_messages_failed",
            topic=topic,
            partition=partition,
            error=str(e),
        )
        raise HTTPException(
            status_code=503,
            detail=f"Failed to browse messages: {str(e)}",
        )


@router.get(
    "/{topic}/encoding",
    response_model=EncodingDetectionResult,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Detect message encoding",
    description="Analyzes a sample of messages from a topic to detect the predominant encoding format.",
)
async def detect_topic_encoding(
    topic: str,
    sample_size: int = Query(100, ge=1, le=1000, description="Number of messages to sample"),
    partition: int = Query(0, description="Partition to sample from"),
    encoding_service: EncodingService = Depends(get_encoding_service),
) -> EncodingDetectionResult:
    """
    Detect encoding for messages in a topic.

    Args:
        topic: Topic name.
        sample_size: Number of messages to sample.
        partition: Partition to sample from.
        encoding_service: Encoding service.

    Returns:
        EncodingDetectionResult with detected encodings.

    Raises:
        HTTPException: If topic not found or broker unavailable.
    """
    try:
        logger.info(
            "detecting_topic_encoding",
            topic=topic,
            sample_size=sample_size,
            partition=partition,
        )

        result = await encoding_service.detect_topic_encoding(
            topic=topic,
            partition=partition,
            sample_size=sample_size,
        )

        logger.info("topic_encoding_detected", topic=topic, encoding=result.primary_encoding)
        return result

    except Exception as e:
        logger.error("detect_topic_encoding_failed", topic=topic, error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to detect encoding: {str(e)}",
        )
