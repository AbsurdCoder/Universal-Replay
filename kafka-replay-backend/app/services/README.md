# Encoding Service

This document provides an overview of the encoding detection and validation service for the Kafka replay tool backend.

## Overview

The encoding service is responsible for detecting, validating, and decoding message payloads from Kafka. It supports multiple encoding formats and uses a layered approach to determine the correct encoding with high accuracy.

## Key Components

- **`encoding_service.py`**: The main service class that provides a unified interface for all encoding-related operations.
- **`encoding_detector.py`**: Implements the core logic for detecting message encoding using a series of heuristics.
- **`encoding_validator.py`**: Validates a message payload against a declared encoding type.
- **`encoding_decoder.py`**: Decodes a message payload for display purposes based on its detected encoding.
- **`schema_registry_client.py`**: An asynchronous HTTP client for interacting with a Confluent Schema Registry, complete with a lightweight in-memory LRU cache.
- **`encoding_models.py`**: Contains all Pydantic models used for request/response data structures, such as `EncodingResult` and `ValidationResult`.

## Features

- **Multi-Format Support**: The service can detect and validate the following formats:
    - JSON
    - Avro (with Schema Registry integration)
    - Protobuf (with Schema Registry integration)
    - UTF-8 plain text
    - Binary / unknown

- **Layered Detection Logic**: To improve accuracy, the service uses a layered detection approach:
    1.  **Byte Heuristics**: Checks for magic bytes (e.g., `0x00` for Avro).
    2.  **Parsing Attempts**: Attempts to parse the payload as JSON.
    3.  **Schema Registry Lookup**: Queries the Schema Registry for a schema associated with the topic.
    4.  **UTF-8 Fallback**: Attempts to decode the payload as a UTF-8 string.
    5.  **Binary Default**: If all else fails, the payload is treated as binary.

- **Async Schema Registry Client**: The `SchemaRegistryClient` is fully asynchronous, using `httpx` for non-blocking I/O. It includes a simple in-memory LRU cache with a configurable TTL to reduce network requests and improve performance.

- **Typed Error Handling**: The service is designed to never raise unhandled exceptions. Instead, it returns typed result objects (e.g., `ValidationResult`) that contain detailed error information if an operation fails.

## Usage

The `EncodingService` is designed to be instantiated once and used throughout the application. It should be initialized during application startup to allow the `SchemaRegistryClient` to establish its connection.

```python
# In your application startup
from app.services.encoding_service import EncodingService

encoding_service = EncodingService(schema_registry_url="http://localhost:8081")
await encoding_service.connect()

# In a request handler
async def handle_message(raw_bytes: bytes, topic: str):
    # Detect, validate, and decode the message
    results = await encoding_service.process_message(raw_bytes, topic)
    return results

# In your application shutdown
await encoding_service.disconnect()
```
