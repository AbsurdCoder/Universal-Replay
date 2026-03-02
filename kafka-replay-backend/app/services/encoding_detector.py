"""
Encoding detection logic with layered heuristics.

Implements intelligent encoding detection using byte patterns, parsing attempts,
and Schema Registry lookups.
"""

import json
import struct
import asyncio
import structlog
from typing import Optional, Tuple

from .encoding_models import (
    EncodingType,
    EncodingResult,
    EncodingDetectionConfig,
)
from .schema_registry_client import SchemaRegistryClient

logger = structlog.get_logger(__name__)


class EncodingDetector:
    """
    Detects message encoding using layered heuristics.

    Detection order:
    1. Magic byte checks (Avro 0x00, Protobuf varint)
    2. JSON parsing attempt
    3. Schema Registry lookup
    4. UTF-8 text attempt
    5. Binary fallback
    """

    def __init__(
        self,
        schema_registry_client: Optional[SchemaRegistryClient] = None,
        config: Optional[EncodingDetectionConfig] = None,
    ):
        """
        Initialize encoding detector.

        Args:
            schema_registry_client: Optional Schema Registry client.
            config: Optional detection configuration.
        """
        self.schema_registry_client = schema_registry_client
        self.config = config or EncodingDetectionConfig()

    async def detect_encoding(
        self,
        raw_bytes: bytes,
        topic: str,
    ) -> EncodingResult:
        """
        Detect encoding of a message using layered heuristics.

        Detection order:
        1. Avro (magic byte 0x00)
        2. JSON (parsing attempt)
        3. Schema Registry lookup
        4. UTF-8 text
        5. Binary

        Args:
            raw_bytes: Raw message bytes.
            topic: Topic name (used for Schema Registry lookup).

        Returns:
            EncodingResult with detected encoding and confidence.
        """
        if not raw_bytes:
            return EncodingResult(
                detected_encoding=EncodingType.BINARY,
                confidence=1.0,
                detection_method="empty_message",
                error="Empty message",
            )

        # Check message size
        if len(raw_bytes) > self.config.max_message_size_bytes:
            return EncodingResult(
                detected_encoding=EncodingType.BINARY,
                confidence=0.0,
                detection_method="size_check",
                error=f"Message exceeds max size of {self.config.max_message_size_bytes} bytes",
            )

        # Layer 1: Check magic bytes (Avro)
        if self.config.enable_avro_detection:
            avro_result = await self._detect_avro(raw_bytes)
            if avro_result:
                return avro_result

        # Layer 2: Try JSON parsing
        if self.config.enable_json_detection:
            json_result = await self._detect_json(raw_bytes)
            if json_result:
                return json_result

        # Layer 3: Schema Registry lookup
        if self.schema_registry_client and self.config.enable_avro_detection:
            registry_result = await self._detect_via_schema_registry(raw_bytes, topic)
            if registry_result:
                return registry_result

        # Layer 4: Try UTF-8 text
        if self.config.enable_utf8_detection:
            utf8_result = await self._detect_utf8(raw_bytes)
            if utf8_result:
                return utf8_result

        # Layer 5: Binary fallback
        return EncodingResult(
            detected_encoding=EncodingType.BINARY,
            confidence=1.0,
            detection_method="binary_fallback",
        )

    async def _detect_avro(self, raw_bytes: bytes) -> Optional[EncodingResult]:
        """
        Detect Avro encoding by checking magic byte.

        Avro messages start with magic byte 0x00 followed by 4-byte schema ID.

        Args:
            raw_bytes: Raw message bytes.

        Returns:
            EncodingResult if Avro detected, None otherwise.
        """
        try:
            if len(raw_bytes) < 5:
                return None

            # Check magic byte
            if raw_bytes[0] != 0x00:
                return None

            # Extract schema ID (big-endian)
            schema_id = struct.unpack(">I", raw_bytes[1:5])[0]

            logger.debug("avro_detected", schema_id=schema_id)

            return EncodingResult(
                detected_encoding=EncodingType.AVRO,
                confidence=0.95,
                schema_id=schema_id,
                detection_method="magic_byte",
                metadata={"magic_byte": "0x00", "schema_id": schema_id},
            )

        except Exception as e:
            logger.debug("avro_detection_failed", error=str(e))
            return None

    async def _detect_json(self, raw_bytes: bytes) -> Optional[EncodingResult]:
        """
        Detect JSON encoding by attempting to parse.

        Args:
            raw_bytes: Raw message bytes.

        Returns:
            EncodingResult if JSON detected, None otherwise.
        """
        try:
            # Run JSON parsing in a task with timeout
            try:
                text = raw_bytes.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                return None

            # Try to parse JSON with timeout
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    json.loads,
                    text,
                ),
                timeout=self.config.json_parse_timeout_ms / 1000.0,
            )

            logger.debug("json_detected")

            return EncodingResult(
                detected_encoding=EncodingType.JSON,
                confidence=0.9,
                detection_method="parse_attempt",
            )

        except (json.JSONDecodeError, UnicodeDecodeError, asyncio.TimeoutError):
            return None
        except Exception as e:
            logger.debug("json_detection_failed", error=str(e))
            return None

    async def _detect_via_schema_registry(
        self,
        raw_bytes: bytes,
        topic: str,
    ) -> Optional[EncodingResult]:
        """
        Detect encoding by looking up schema in Schema Registry.

        Args:
            raw_bytes: Raw message bytes.
            topic: Topic name.

        Returns:
            EncodingResult if schema found, None otherwise.
        """
        try:
            if not self.schema_registry_client:
                return None

            # Try to get latest schema for topic
            schema = await self.schema_registry_client.get_latest_schema(topic)
            if not schema:
                return None

            # Map schema type to encoding type
            schema_type_map = {
                "AVRO": EncodingType.AVRO,
                "PROTOBUF": EncodingType.PROTOBUF,
                "JSON": EncodingType.JSON,
            }

            encoding_type = schema_type_map.get(
                schema.schema_type.upper(),
                EncodingType.UNKNOWN,
            )

            logger.debug(
                "encoding_detected_via_registry",
                topic=topic,
                schema_type=schema.schema_type,
                schema_id=schema.schema_id,
            )

            return EncodingResult(
                detected_encoding=encoding_type,
                confidence=0.85,
                schema_id=schema.schema_id,
                schema_version=schema.schema_version,
                detection_method="schema_registry",
                metadata={
                    "schema_subject": schema.schema_subject,
                    "schema_type": schema.schema_type,
                },
            )

        except Exception as e:
            logger.debug("schema_registry_detection_failed", error=str(e))
            return None

    async def _detect_utf8(self, raw_bytes: bytes) -> Optional[EncodingResult]:
        """
        Detect UTF-8 text encoding.

        Args:
            raw_bytes: Raw message bytes.

        Returns:
            EncodingResult if valid UTF-8 text, None otherwise.
        """
        try:
            # Try to decode as UTF-8
            loop = asyncio.get_event_loop()
            text = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    raw_bytes.decode,
                    "utf-8",
                ),
                timeout=self.config.utf8_decode_timeout_ms / 1000.0,
            )

            # Check if it looks like text (has printable characters)
            if len(text) > 0:
                printable_count = sum(
                    1 for c in text
                    if c.isprintable() or c.isspace()
                )
                printable_ratio = printable_count / len(text)

                if printable_ratio > 0.8:  # 80% printable
                    logger.debug("utf8_text_detected")

                    return EncodingResult(
                        detected_encoding=EncodingType.UTF8_TEXT,
                        confidence=0.8,
                        detection_method="utf8_decode",
                        metadata={
                            "printable_ratio": printable_ratio,
                            "length": len(text),
                        },
                    )

            return None

        except (UnicodeDecodeError, asyncio.TimeoutError):
            return None
        except Exception as e:
            logger.debug("utf8_detection_failed", error=str(e))
            return None

    def _extract_avro_schema_id(self, raw_bytes: bytes) -> Optional[int]:
        """
        Extract schema ID from Avro message.

        Args:
            raw_bytes: Raw message bytes.

        Returns:
            Schema ID or None if not Avro.
        """
        try:
            if len(raw_bytes) < 5 or raw_bytes[0] != 0x00:
                return None

            schema_id = struct.unpack(">I", raw_bytes[1:5])[0]
            return schema_id

        except Exception:
            return None
