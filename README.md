# Architecture Documentation

## Overview

This document describes the architecture of the Kafka Replay Tool backend, a production-grade FastAPI application designed for replaying Kafka messages with enrichment and filtering capabilities.

## Design Principles

1. **Async-First**: All I/O operations are asynchronous to maximize throughput and minimize resource usage.
2. **No Global Mutable State**: Services are instantiated per-request to ensure thread safety and scalability.
3. **Memory-Efficient Streaming**: Messages are processed as async generators, never loading entire topics into memory.
4. **Separation of Concerns**: Clear boundaries between API, business logic, data access, and external integrations.
5. **Dependency Injection**: Services receive their dependencies through constructor injection.

## Component Architecture

### 1. Core Layer (`app/core/`)

**Purpose**: Application configuration, logging, and lifecycle management.

#### `config.py`
- Loads configuration from environment variables using Pydantic Settings.
- Provides a single `settings` object accessible throughout the application.
- Environment-based configuration for development, staging, and production.

#### `logging.py`
- Configures structured JSON logging using `structlog`.
- Integrates with Python's standard logging library.
- Provides context-aware logging with automatic field injection.

#### `lifespan.py`
- Manages application startup and shutdown events.
- Initializes database connections on startup.
- Gracefully closes connections on shutdown.

### 2. Database Layer (`app/db/`)

**Purpose**: Async database access and ORM management.

#### `session.py`
- Creates and manages async SQLAlchemy engine and session factory.
- Provides dependency injection for database sessions in FastAPI endpoints.
- Configurable connection pooling and recycling.

#### `base.py`
- Defines `BaseModel` with common fields (`id`, `created_at`, `updated_at`).
- Serves as the base class for all database models.

#### `models.py`
- Defines `ReplayJob` model for tracking replay job state.
- Includes status enum, filtering fields, and performance metrics.
- Indexed fields for efficient querying.

### 3. Messaging Abstraction (`app/adapters/`)

**Purpose**: Decoupled interface for messaging operations.

#### `base.py`
- Defines `MessagingAdapter` abstract base class.
- Specifies interface for topic listing, message consumption, and production.
- Enables easy swapping of messaging implementations (e.g., Kafka, RabbitMQ).

#### `kafka.py`
- Implements `MessagingAdapter` using `aiokafka`.
- Provides async methods for Kafka operations.
- **Memory-Efficient Consumption**: Uses async generators to stream messages without loading entire topics.
- Handles connection management and error handling.

### 4. Data Models (`app/models/`)

**Purpose**: Pydantic v2 schemas for request/response validation.

#### `schemas.py`
- Defines all request and response models.
- Includes filtering, progress tracking, and statistics models.
- Provides JSON schema examples for API documentation.

### 5. Services Layer (`app/services/`)

**Purpose**: Business logic encapsulation.

#### `replay_service.py`
- Manages replay job lifecycle (create, read, update, delete).
- Converts database models to response models.
- Handles job status transitions and progress tracking.

#### `topic_service.py`
- Provides operations for Kafka topics.
- Lists topics and retrieves metadata (partition count, offset ranges).

#### `script_service.py`
- Manages enrichment script registration and execution.
- Delegates script execution to the sandbox executor.

#### `encoding_service.py`
- Handles message encoding/decoding (JSON, UTF-8).
- Provides utilities for header encoding/decoding.

### 6. Script Sandbox (`app/sandbox/`)

**Purpose**: Secure execution of user-defined enrichment scripts.

#### `executor.py`
- Uses RestrictedPython to safely execute untrusted code.
- Implements timeout protection to prevent hanging scripts.
- Provides a restricted set of built-in functions.
- Supports both sync and async enrichment functions.

### 7. API Layer (`app/api/v1/`)

**Purpose**: HTTP endpoint definitions.

#### `replays.py`
- CRUD operations for replay jobs.
- Endpoints: `POST /api/v1/replays`, `GET /api/v1/replays`, `GET /api/v1/replays/{id}`, etc.
- Proper error handling and HTTP status codes.

#### `topics.py`
- Topic listing and metadata retrieval.
- Endpoints: `GET /api/v1/topics`, `GET /api/v1/topics/{name}`.

#### `health.py`
- Health and readiness check endpoints.
- Used for Kubernetes liveness and readiness probes.

### 8. Main Application (`app/main.py`)

- Creates FastAPI application instance.
- Registers API routers.
- Configures CORS middleware.
- Sets up lifespan context manager.

## Data Flow

### Replay Job Creation

```
POST /api/v1/replays
    ↓
FastAPI validates request (Pydantic)
    ↓
ReplayService.create_job()
    ↓
Database insert (SQLAlchemy)
    ↓
Response model conversion
    ↓
JSON response
```

### Message Consumption

```
GET /api/v1/replays/{id}/messages
    ↓
ReplayService.get_job()
    ↓
KafkaAdapter.consume_messages()
    ↓
Async generator yields messages one at a time
    ↓
Optional: ScriptService.enrich_message()
    ↓
KafkaAdapter.produce_message()
    ↓
Progress tracking in database
```

## Async/Await Patterns

### Database Operations

```python
async def get_job(self, job_id: UUID) -> Optional[ReplayJobResponse]:
    stmt = select(ReplayJob).where(ReplayJob.job_id == job_id)
    result = await self.session.execute(stmt)
    job = result.scalar_one_or_none()
    return self._to_response(job) if job else None
```

### Kafka Operations

```python
async def consume_messages(self, topic: str, ...) -> AsyncGenerator[Message, None]:
    consumer = AIOKafkaConsumer(...)
    await consumer.start()
    async for message in consumer:
        yield Message(...)
    await consumer.stop()
```

### Script Execution

```python
async def execute(self, script_code: str, function_name: str, *args, **kwargs) -> Any:
    result = await asyncio.wait_for(
        self._run_function(func, args, kwargs),
        timeout=self.timeout
    )
    return result
```

## Scalability Considerations

### Horizontal Scaling

- **Stateless Design**: Each instance can handle any request independently.
- **Multiple Workers**: Uvicorn runs multiple worker processes.
- **Load Balancing**: Deploy behind a load balancer (e.g., Nginx, HAProxy).

### Vertical Scaling

- **Connection Pooling**: Configurable database connection pool.
- **Async I/O**: Handles thousands of concurrent connections with minimal threads.
- **Memory Efficiency**: Async generators prevent memory bloat from large topics.

### Database Optimization

- **Indexes**: Created on frequently queried fields (`job_id`, `source_topic`, `status`).
- **Connection Recycling**: Prevents stale connections.
- **Pool Sizing**: Configurable based on expected concurrency.

## Error Handling

### API Layer

- HTTP exceptions with appropriate status codes.
- Structured error responses with `detail` and `error_code`.
- Logging of all errors with context.

### Service Layer

- Validation errors raised as `ValueError`.
- Database errors propagated with context.
- Graceful degradation where possible.

### Kafka Layer

- Connection errors trigger reconnection logic.
- Timeout errors are caught and reported.
- Consumer group management handles rebalancing.

## Security Considerations

### Script Sandbox

- RestrictedPython prevents access to dangerous functions.
- Timeout protection prevents DoS attacks.
- Limited built-in functions reduce attack surface.

### Database

- Parameterized queries prevent SQL injection.
- Connection pooling with SSL/TLS support.
- User authentication and authorization (future enhancement).

### API

- CORS configuration for frontend access.
- Rate limiting (future enhancement).
- Authentication and authorization (future enhancement).

## Testing Strategy

### Unit Tests

- Test individual services in isolation.
- Mock external dependencies (Kafka, database).
- Use `pytest-asyncio` for async test support.

### Integration Tests

- Test service interactions.
- Use test database and Kafka containers.
- Verify end-to-end workflows.

### Load Testing

- Use tools like `locust` or `k6` to test throughput.
- Monitor resource usage under load.
- Identify bottlenecks and optimize.

## Deployment

### Docker

- Multi-stage Dockerfile for optimized image size.
- Non-root user for security.
- Health checks for orchestration platforms.

### Kubernetes

- Deployment with multiple replicas.
- Service for load balancing.
- ConfigMap for environment configuration.
- Secrets for sensitive data.
- Horizontal Pod Autoscaler for dynamic scaling.

### Monitoring

- Structured logging for log aggregation (ELK, Datadog).
- Prometheus metrics (future enhancement).
- Distributed tracing (future enhancement).

## Future Enhancements

1. **Authentication & Authorization**: JWT-based API authentication.
2. **Rate Limiting**: Per-user or per-IP rate limiting.
3. **Metrics & Monitoring**: Prometheus metrics and Grafana dashboards.
4. **Distributed Tracing**: OpenTelemetry integration.
5. **Advanced Filtering**: JSONPath-based payload filtering.
6. **Message Transformation**: More sophisticated enrichment capabilities.
7. **Batch Operations**: Bulk job creation and management.
8. **Webhooks**: Event notifications for job completion.
