"""
Async Schema Registry client with LRU caching.

Provides async HTTP client for interacting with Confluent Schema Registry
with built-in LRU caching to reduce network requests.
"""

import httpx
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict
import json

from .encoding_models import SchemaMetadata

logger = structlog.get_logger(__name__)


class CacheEntry:
    """Entry in the LRU cache."""

    def __init__(self, value: Any, ttl_seconds: int = 60):
        """
        Initialize cache entry.

        Args:
            value: Value to cache.
            ttl_seconds: Time to live in seconds.
        """
        self.value = value
        self.created_at = datetime.utcnow()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds


class LRUCache:
    """
    Simple LRU cache with TTL support.

    Stores up to max_size entries, evicting least recently used entries
    when capacity is reached.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 60):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries.
            ttl_seconds: Default TTL for entries in seconds.
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found or expired.
        """
        if key not in self.cache:
            return None

        entry = self.cache[key]

        # Check if expired
        if entry.is_expired():
            del self.cache[key]
            logger.debug("cache_entry_expired", key=key)
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        logger.debug("cache_hit", key=key)
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl_seconds: Optional TTL override.
        """
        ttl = ttl_seconds or self.ttl_seconds

        # If key already exists, remove it first
        if key in self.cache:
            del self.cache[key]

        # Add new entry
        self.cache[key] = CacheEntry(value, ttl)

        # Evict LRU entry if over capacity
        if len(self.cache) > self.max_size:
            evicted_key, _ = self.cache.popitem(last=False)
            logger.debug("cache_entry_evicted", key=evicted_key)

        logger.debug("cache_set", key=key, ttl=ttl)

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        logger.info("cache_cleared")

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed.
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug("cache_cleanup", removed_count=len(expired_keys))

        return len(expired_keys)


class SchemaRegistryClient:
    """
    Async HTTP client for Confluent Schema Registry.

    Provides methods for fetching schemas with built-in LRU caching.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        timeout_seconds: float = 10.0,
        cache_ttl_seconds: int = 60,
        cache_max_size: int = 1000,
    ):
        """
        Initialize Schema Registry client.

        Args:
            base_url: Base URL of Schema Registry.
            timeout_seconds: Request timeout in seconds.
            cache_ttl_seconds: Cache TTL in seconds.
            cache_max_size: Maximum cache size.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.cache = LRUCache(max_size=cache_max_size, ttl_seconds=cache_ttl_seconds)
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Initialize async HTTP client."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        )
        logger.info("schema_registry_client_connected", base_url=self.base_url)

    async def disconnect(self) -> None:
        """Close async HTTP client."""
        if self.client:
            await self.client.aclose()
        logger.info("schema_registry_client_disconnected")

    async def get_schema_by_id(self, schema_id: int) -> Optional[SchemaMetadata]:
        """
        Get schema by ID.

        Args:
            schema_id: Schema ID.

        Returns:
            SchemaMetadata or None if not found.
        """
        cache_key = f"schema_id:{schema_id}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return SchemaMetadata(**cached, cached=True)

        try:
            if not self.client:
                logger.error("schema_registry_client_not_connected")
                return None

            response = await self.client.get(f"/schemas/ids/{schema_id}")
            response.raise_for_status()

            data = response.json()

            schema_metadata = SchemaMetadata(
                schema_id=schema_id,
                schema_type=data.get("schemaType", "AVRO"),
                schema_content=data.get("schema", ""),
                references=data.get("references", []),
            )

            # Cache the result
            self.cache.set(cache_key, schema_metadata.model_dump())

            logger.info("schema_fetched_by_id", schema_id=schema_id)
            return schema_metadata

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("schema_not_found", schema_id=schema_id)
            else:
                logger.error(
                    "schema_registry_error",
                    schema_id=schema_id,
                    status_code=e.response.status_code,
                    error=str(e),
                )
            return None

        except Exception as e:
            logger.error(
                "schema_registry_request_failed",
                schema_id=schema_id,
                error=str(e),
            )
            return None

    async def get_schema_by_subject(
        self,
        subject: str,
        version: str = "latest",
    ) -> Optional[SchemaMetadata]:
        """
        Get schema by subject and version.

        Args:
            subject: Schema subject (usually topic name).
            version: Schema version (default: "latest").

        Returns:
            SchemaMetadata or None if not found.
        """
        cache_key = f"schema_subject:{subject}:{version}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return SchemaMetadata(**cached, cached=True)

        try:
            if not self.client:
                logger.error("schema_registry_client_not_connected")
                return None

            response = await self.client.get(
                f"/subjects/{subject}/versions/{version}"
            )
            response.raise_for_status()

            data = response.json()

            schema_metadata = SchemaMetadata(
                schema_id=data.get("id"),
                schema_version=data.get("version"),
                schema_type=data.get("schemaType", "AVRO"),
                schema_subject=subject,
                schema_content=data.get("schema", ""),
                references=data.get("references", []),
            )

            # Cache the result
            self.cache.set(cache_key, schema_metadata.model_dump())

            logger.info(
                "schema_fetched_by_subject",
                subject=subject,
                version=version,
                schema_id=schema_metadata.schema_id,
            )
            return schema_metadata

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    "schema_subject_not_found",
                    subject=subject,
                    version=version,
                )
            else:
                logger.error(
                    "schema_registry_error",
                    subject=subject,
                    version=version,
                    status_code=e.response.status_code,
                    error=str(e),
                )
            return None

        except Exception as e:
            logger.error(
                "schema_registry_request_failed",
                subject=subject,
                version=version,
                error=str(e),
            )
            return None

    async def get_subjects(self) -> Optional[list[str]]:
        """
        Get all registered subjects.

        Returns:
            List of subjects or None if request fails.
        """
        cache_key = "all_subjects"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug("subjects_from_cache")
            return cached

        try:
            if not self.client:
                logger.error("schema_registry_client_not_connected")
                return None

            response = await self.client.get("/subjects")
            response.raise_for_status()

            subjects = response.json()

            # Cache the result
            self.cache.set(cache_key, subjects)

            logger.info("subjects_fetched", count=len(subjects))
            return subjects

        except Exception as e:
            logger.error("fetch_subjects_failed", error=str(e))
            return None

    async def get_latest_schema(self, subject: str) -> Optional[SchemaMetadata]:
        """
        Get the latest schema for a subject.

        Args:
            subject: Schema subject.

        Returns:
            SchemaMetadata or None if not found.
        """
        return await self.get_schema_by_subject(subject, "latest")

    async def health_check(self) -> bool:
        """
        Check if Schema Registry is healthy.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            if not self.client:
                return False

            response = await self.client.get("/")
            return response.status_code == 200

        except Exception as e:
            logger.warning("schema_registry_health_check_failed", error=str(e))
            return False

    def clear_cache(self) -> None:
        """Clear all cached schemas."""
        self.cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        return {
            "cache_size": self.cache.size(),
            "cache_max_size": self.cache.max_size,
            "cache_ttl_seconds": self.cache.ttl_seconds,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
