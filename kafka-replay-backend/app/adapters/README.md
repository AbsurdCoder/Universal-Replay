"""
# Messaging Abstraction Layer

This directory contains the messaging abstraction layer for the Kafka replay tool.
It provides a standardized interface for interacting with message brokers, with a
concrete implementation for Apache Kafka.

## Key Components

- **`base.py`**: Defines the `BaseMessagingAdapter` abstract base class, which
  specifies the contract for all messaging adapters.

- **`kafka.py`**: Implements the `KafkaAdapter` class, a concrete implementation
  of `BaseMessagingAdapter` using the `aiokafka` library.

- **`models.py`**: Contains Pydantic models for all data structures used in the
  messaging layer (e.g., `TopicInfo`, `RawMessage`, `ProduceResult`).

- **`exceptions.py`**: Defines custom, typed exceptions for the messaging layer
  (e.g., `KafkaBrokerError`, `TopicNotFoundError`).

- **`config.py`**: Manages Kafka-specific configuration using `pydantic-settings`,
  allowing for environment variable-based setup.

- **`pool.py`**: Implements a `KafkaConnectionPool` for managing and reusing
  Kafka connections, improving performance and resilience.

- **`error_handler.py`**: Provides utilities for handling and recovering from
  messaging errors, including a circuit breaker and retry decorator.

## Design Principles

- **Abstraction**: The `BaseMessagingAdapter` allows for easy extension to
  support other message brokers in the future (e.g., RabbitMQ, Pulsar).

- **Async-First**: All I/O operations are asynchronous, using `async/await`
  and `async generators` to ensure non-blocking performance.

- **Memory Efficiency**: The `consume_messages` method is an async generator,
  which streams messages from Kafka without buffering the entire topic in memory.

- **Resilience**: The layer includes a connection pool, health checks, a circuit
  breaker, and automatic retries with exponential backoff to handle broker
  unavailability and other transient failures gracefully.

- **Configuration over Code**: All Kafka settings are managed through environment
  variables, making it easy to configure the application for different
  environments (dev, staging, prod).

- **Typed and Testable**: All components are fully typed, and the modular design
  makes it easy to write unit and integration tests.

## Usage

The `AdapterLifecycleManager` in `pool.py` is the recommended way to manage the
adapter's lifecycle. It should be initialized during application startup and
shut down gracefully on exit.

```python
from app.adapters.pool import AdapterLifecycleManager
from app.adapters.config import KafkaSettings

# In your application's startup event
async def startup():
    kafka_settings = KafkaSettings()
    adapter_manager = AdapterLifecycleManager(kafka_settings)
    await adapter_manager.startup()
    # Store adapter_manager in app state for later use

# In your application's shutdown event
async def shutdown():
    await adapter_manager.shutdown()

# To use the adapter in a request handler
async def list_topics():
    async with adapter_manager.acquire() as adapter:
        topics = await adapter.list_topics()
        return topics
```
"""""
