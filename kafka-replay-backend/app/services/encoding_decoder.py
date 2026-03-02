"""
Display decoding logic for different encodings.

Decodes messages for display/preview purposes.
"""

import json
import struct
import base64
import structlog
from typing import Optional, Dict, Any, Union

from .encoding_models import (
    EncodingType,
    EncodingResult,
    DecodeResult,
)
from .schema_registry_client import SchemaRegistryClient

logger = structlog.get_logger(__name__)


class EncodingDecoder:
    """Decodes messages for display based on their encoding."""

    def __init__(
        self,
        schema_registry_client: Optional[SchemaRegistryClient] = None,
        max_preview_length: int = 500,
    ):
        """
        Initialize encoding decoder.

        Args:
            schema_registry_client: Optional Schema Registry client.
            max_preview_length: Maximum length for preview strings.
        """
        self.schema_registry_client = schema_registry_client
        self.max_preview_length = max_preview_length

    async def decode_for_display(
        self,
        raw_bytes: bytes,
        encoding_result: EncodingResult,
    ) -> DecodeResult:
        """
        Decode a message for display based on detected encoding.

        Args:
            raw_bytes: Raw message bytes.
            encoding_result: EncodingResult from detection.

        Returns:
            DecodeResult with decoded content.
        """
        try:
            encoding_type = encoding_result.detected_encoding

            if encoding_type == EncodingType.JSON:
                return await self._decode_json(raw_bytes)
            elif encoding_type == EncodingType.AVRO:
                return await self._decode_avro(raw_bytes, encoding_result)
            elif encoding_type == EncodingType.PROTOBUF:
                return await self._decode_protobuf(raw_bytes, encoding_result)
            elif encoding_type == EncodingType.UTF8_TEXT:
                return await self._decode_utf8(raw_bytes)
            elif encoding_type == EncodingType.BINARY:
                return await self._decode_binary(raw_bytes)
            else:
                return DecodeResult(
                    success=False,
                    encoding=encoding_type,
                    error="Unsupported encoding type",
                    size_bytes=len(raw_bytes),
                )

        except Exception as e:
            logger.error("decode_error", error=str(e))
            return DecodeResult(
                success=False,
                encoding=encoding_result.detected_encoding,
                error=f"Decoding failed: {str(e)}",
                size_bytes=len(raw_bytes),
            )

    async def _decode_json(self, raw_bytes: bytes) -> DecodeResult:
        """Decode JSON message."""
        try:
            text = raw_bytes.decode("utf-8", errors="replace")
            content = json.loads(text)

            preview = self._create_preview(json.dumps(content, indent=2))

            logger.debug("json_decoded")

            return DecodeResult(
                success=True,
                content=content,
                encoding=EncodingType.JSON,
                preview=preview,
                size_bytes=len(raw_bytes),
            )

        except Exception as e:
            logger.error("json_decode_failed", error=str(e))
            return DecodeResult(
                success=False,
                encoding=EncodingType.JSON,
                error=f"JSON decode failed: {str(e)}",
                size_bytes=len(raw_bytes),
            )

    async def _decode_avro(
        self,
        raw_bytes: bytes,
        encoding_result: EncodingResult,
    ) -> DecodeResult:
        """Decode Avro message."""
        try:
            if len(raw_bytes) < 5:
                raise ValueError("Message too short for Avro")

            # Extract schema ID
            schema_id = struct.unpack(">I", raw_bytes[1:5])[0]

            # Try to fetch schema
            schema_info = None
            if self.schema_registry_client:
                schema_info = await self.schema_registry_client.get_schema_by_id(
                    schema_id
                )

            # For now, return metadata without full deserialization
            # (full Avro deserialization requires avro library)
            content = {
                "schema_id": schema_id,
                "message_size": len(raw_bytes),
                "payload_size": len(raw_bytes) - 5,
                "schema_cached": schema_info.cached if schema_info else False,
            }

            if schema_info:
                content["schema_type"] = schema_info.schema_type
                content["schema_subject"] = schema_info.schema_subject

            preview = f"Avro message (schema_id={schema_id}, size={len(raw_bytes)} bytes)"

            logger.debug("avro_decoded", schema_id=schema_id)

            return DecodeResult(
                success=True,
                content=content,
                encoding=EncodingType.AVRO,
                preview=preview,
                size_bytes=len(raw_bytes),
            )

        except Exception as e:
            logger.error("avro_decode_failed", error=str(e))
            return DecodeResult(
                success=False,
                encoding=EncodingType.AVRO,
                error=f"Avro decode failed: {str(e)}",
                size_bytes=len(raw_bytes),
            )

    async def _decode_protobuf(
        self,
        raw_bytes: bytes,
        encoding_result: EncodingResult,
    ) -> DecodeResult:
        """Decode Protobuf message."""
        try:
            # Protobuf decoding requires descriptors
            # For now, return metadata
            content = {
                "message_size": len(raw_bytes),
                "note": "Full Protobuf deserialization requires registered descriptors",
            }

            preview = f"Protobuf message (size={len(raw_bytes)} bytes)"

            logger.debug("protobuf_decoded")

            return DecodeResult(
                success=True,
                content=content,
                encoding=EncodingType.PROTOBUF,
                preview=preview,
                size_bytes=len(raw_bytes),
            )

        except Exception as e:
            logger.error("protobuf_decode_failed", error=str(e))
            return DecodeResult(
                success=False,
                encoding=EncodingType.PROTOBUF,
                error=f"Protobuf decode failed: {str(e)}",
                size_bytes=len(raw_bytes),
            )

    async def _decode_utf8(self, raw_bytes: bytes) -> DecodeResult:
        """Decode UTF-8 text message."""
        try:
            text = raw_bytes.decode("utf-8", errors="replace")
            preview = self._create_preview(text)

            logger.debug("utf8_decoded", length=len(text))

            return DecodeResult(
                success=True,
                content=text,
                encoding=EncodingType.UTF8_TEXT,
                preview=preview,
                size_bytes=len(raw_bytes),
            )

        except Exception as e:
            logger.error("utf8_decode_failed", error=str(e))
            return DecodeResult(
                success=False,
                encoding=EncodingType.UTF8_TEXT,
                error=f"UTF-8 decode failed: {str(e)}",
                size_bytes=len(raw_bytes),
            )

    async def _decode_binary(self, raw_bytes: bytes) -> DecodeResult:
        """Decode binary message."""
        try:
            # Show hex representation
            hex_str = raw_bytes.hex()
            preview = self._create_preview(hex_str, separator=" ")

            # Create content dict
            content = {
                "hex": hex_str,
                "size": len(raw_bytes),
                "base64": base64.b64encode(raw_bytes).decode("ascii"),
            }

            logger.debug("binary_decoded", size=len(raw_bytes))

            return DecodeResult(
                success=True,
                content=content,
                encoding=EncodingType.BINARY,
                preview=preview,
                size_bytes=len(raw_bytes),
            )

        except Exception as e:
            logger.error("binary_decode_failed", error=str(e))
            return DecodeResult(
                success=False,
                encoding=EncodingType.BINARY,
                error=f"Binary decode failed: {str(e)}",
                size_bytes=len(raw_bytes),
            )

    def _create_preview(
        self,
        content: str,
        separator: str = "",
    ) -> str:
        """
        Create a preview of content.

        Args:
            content: Content to preview.
            separator: Separator to use between chunks (for hex).

        Returns:
            Preview string (truncated if needed).
        """
        if len(content) <= self.max_preview_length:
            return content

        # Truncate and add ellipsis
        preview = content[: self.max_preview_length - 3]
        if separator:
            # For hex, truncate at word boundary
            preview = preview.rsplit(separator, 1)[0]

        return preview + "..."
