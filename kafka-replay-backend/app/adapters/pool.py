"""
Connection pool manager for Kafka adapter.

Manages reusable connections to Kafka broker with lifecycle management.
Ensures connections are properly initialized, monitored, and cleaned up.
"""

from typing import Optional, List
import asyncio
import structlog
from contextlib import asynccontextmanager

from .kafka import KafkaAdapter
from .config import KafkaSettings
from .exceptions import MessagingAdapterError, KafkaBrokerError

logger = structlog.get_logger(__name__)


class KafkaConnectionPool:
    """
    Connection pool for Kafka adapters.

    Manages a pool of reusable Kafka adapter instances with health monitoring
    and automatic reconnection on failure.
    """

    def __init__(
        self,
        settings: KafkaSettings,
        pool_size: int = 1,
    ):
        """
        Initialize connection pool.

        Args:
            settings: KafkaSettings instance.
            pool_size: Number of connections to maintain in the pool.
        """
        self.settings = settings
        self.pool_size = max(1, pool_size)
        self.adapters: List[KafkaAdapter] = []
        self._current_index = 0
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize all connections in the pool.

        Raises:
            KafkaBrokerError: If unable to connect to broker.
            MessagingAdapterError: If initialization fails.
        """
        if self._initialized:
            logger.warning("pool_already_initialized")
            return

        try:
            logger.info("initializing_kafka_connection_pool", pool_size=self.pool_size)

            for i in range(self.pool_size):
                adapter = KafkaAdapter(self.settings)
                try:
                    await adapter.connect()
                    self.adapters.append(adapter)
                    logger.info(
                        "adapter_connected",
                        adapter_index=i,
                        total=self.pool_size,
                    )
                except Exception as e:
                    logger.error(
                        "adapter_connection_failed",
                        adapter_index=i,
                        error=str(e),
                    )
                    # Clean up any previously connected adapters
                    for connected_adapter in self.adapters:
                        try:
                            await connected_adapter.disconnect()
                        except Exception as cleanup_error:
                            logger.error(
                                "cleanup_error",
                                error=str(cleanup_error),
                            )
                    raise

            self._initialized = True
            logger.info("kafka_connection_pool_initialized", pool_size=len(self.adapters))

        except (KafkaBrokerError, MessagingAdapterError):
            raise
        except Exception as e:
            logger.error("pool_initialization_failed", error=str(e))
            raise MessagingAdapterError(f"Failed to initialize connection pool: {str(e)}")

    async def shutdown(self) -> None:
        """
        Shutdown all connections in the pool.

        Gracefully closes all adapters.
        """
        try:
            logger.info("shutting_down_kafka_connection_pool")

            for i, adapter in enumerate(self.adapters):
                try:
                    await adapter.disconnect()
                    logger.info("adapter_disconnected", adapter_index=i)
                except Exception as e:
                    logger.error(
                        "adapter_disconnect_error",
                        adapter_index=i,
                        error=str(e),
                    )

            self.adapters.clear()
            self._initialized = False
            logger.info("kafka_connection_pool_shutdown")

        except Exception as e:
            logger.error("pool_shutdown_error", error=str(e))

    async def get_adapter(self) -> KafkaAdapter:
        """
        Get an adapter from the pool.

        Uses round-robin selection to distribute load across adapters.
        Performs health check before returning.

        Returns:
            KafkaAdapter instance.

        Raises:
            MessagingAdapterError: If no healthy adapters available.
        """
        if not self._initialized or not self.adapters:
            raise MessagingAdapterError("Connection pool not initialized")

        async with self._lock:
            # Try to find a healthy adapter
            attempts = 0
            max_attempts = len(self.adapters)

            while attempts < max_attempts:
                adapter = self.adapters[self._current_index % len(self.adapters)]
                self._current_index += 1

                try:
                    if await adapter.health_check():
                        logger.debug(
                            "adapter_selected",
                            index=self._current_index - 1,
                        )
                        return adapter
                except Exception as e:
                    logger.warning(
                        "adapter_health_check_failed",
                        index=self._current_index - 1,
                        error=str(e),
                    )

                attempts += 1

            # No healthy adapters found
            logger.error("no_healthy_adapters_available")
            raise MessagingAdapterError("No healthy Kafka adapters available in pool")

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire an adapter from the pool as a context manager.

        Usage:
            async with pool.acquire() as adapter:
                await adapter.list_topics()

        Yields:
            KafkaAdapter instance.
        """
        adapter = await self.get_adapter()
        try:
            yield adapter
        except Exception as e:
            logger.error("adapter_operation_failed", error=str(e))
            raise

    async def reconnect_failed_adapters(self) -> int:
        """
        Attempt to reconnect any failed adapters.

        Returns:
            Number of adapters successfully reconnected.
        """
        reconnected = 0

        for i, adapter in enumerate(self.adapters):
            try:
                if not await adapter.health_check():
                    logger.info("reconnecting_adapter", index=i)
                    await adapter.disconnect()
                    await adapter.connect()
                    reconnected += 1
                    logger.info("adapter_reconnected", index=i)
            except Exception as e:
                logger.error(
                    "adapter_reconnection_failed",
                    index=i,
                    error=str(e),
                )

        if reconnected > 0:
            logger.info("adapters_reconnected", count=reconnected)

        return reconnected

    async def health_check(self) -> bool:
        """
        Check health of the entire pool.

        Returns:
            True if at least one adapter is healthy, False otherwise.
        """
        if not self._initialized or not self.adapters:
            return False

        for adapter in self.adapters:
            try:
                if await adapter.health_check():
                    return True
            except Exception:
                pass

        return False

    def is_initialized(self) -> bool:
        """Check if pool is initialized."""
        return self._initialized

    def get_pool_size(self) -> int:
        """Get current pool size."""
        return len(self.adapters)


class AdapterLifecycleManager:
    """
    Manages the lifecycle of Kafka adapter and connection pool.

    Handles initialization, health monitoring, and graceful shutdown.
    """

    def __init__(self, settings: KafkaSettings, pool_size: int = 1):
        """
        Initialize lifecycle manager.

        Args:
            settings: KafkaSettings instance.
            pool_size: Size of connection pool.
        """
        self.settings = settings
        self.pool_size = pool_size
        self.pool: Optional[KafkaConnectionPool] = None
        self._health_check_task: Optional[asyncio.Task] = None

    async def startup(self) -> None:
        """
        Initialize adapter and connection pool.

        Called during application startup.

        Raises:
            KafkaBrokerError: If unable to connect to broker.
            MessagingAdapterError: If initialization fails.
        """
        try:
            logger.info("starting_adapter_lifecycle_manager")

            self.pool = KafkaConnectionPool(self.settings, self.pool_size)
            await self.pool.initialize()

            # Start health check task
            self._health_check_task = asyncio.create_task(
                self._health_check_loop()
            )

            logger.info("adapter_lifecycle_manager_started")

        except Exception as e:
            logger.error("adapter_startup_failed", error=str(e))
            raise

    async def shutdown(self) -> None:
        """
        Shutdown adapter and connection pool.

        Called during application shutdown.
        """
        try:
            logger.info("shutting_down_adapter_lifecycle_manager")

            # Cancel health check task
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            # Shutdown pool
            if self.pool:
                await self.pool.shutdown()

            logger.info("adapter_lifecycle_manager_shutdown")

        except Exception as e:
            logger.error("adapter_shutdown_error", error=str(e))

    async def get_adapter(self) -> KafkaAdapter:
        """
        Get an adapter from the pool.

        Returns:
            KafkaAdapter instance.

        Raises:
            MessagingAdapterError: If pool not initialized or no adapters available.
        """
        if not self.pool:
            raise MessagingAdapterError("Adapter not initialized")

        return await self.pool.get_adapter()

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire an adapter as a context manager.

        Yields:
            KafkaAdapter instance.
        """
        if not self.pool:
            raise MessagingAdapterError("Adapter not initialized")

        async with self.pool.acquire() as adapter:
            yield adapter

    async def _health_check_loop(self) -> None:
        """
        Periodically check pool health and reconnect failed adapters.

        Runs in background during application lifetime.
        """
        check_interval = 30  # seconds

        while True:
            try:
                await asyncio.sleep(check_interval)

                if not self.pool:
                    continue

                # Check pool health
                is_healthy = await self.pool.health_check()

                if not is_healthy:
                    logger.warning("pool_health_check_failed")
                    # Attempt to reconnect
                    reconnected = await self.pool.reconnect_failed_adapters()
                    if reconnected > 0:
                        logger.info("pool_recovered", adapters_reconnected=reconnected)
                else:
                    logger.debug("pool_health_check_passed")

            except asyncio.CancelledError:
                logger.info("health_check_loop_cancelled")
                break
            except Exception as e:
                logger.error("health_check_loop_error", error=str(e))

    async def is_healthy(self) -> bool:
        """
        Check if adapter is healthy.

        Returns:
            True if healthy, False otherwise.
        """
        if not self.pool:
            return False

        return await self.pool.health_check()
