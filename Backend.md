# Replay Tool - Backend

This is a production-grade Python FastAPI backend for a Kafka replay tool. It provides a comprehensive set of features for replaying Kafka messages with enrichment and filtering capabilities, all built on a modern, async-first architecture.

## Features

- **Async/Await Throughout**: Fully asynchronous architecture using `asyncio`, `aiokafka`, and `asyncpg`.
- **FastAPI Framework**: Modern, high-performance web framework for building APIs.
- **Pydantic v2 Models**: Robust data validation and serialization for all request/response schemas.
- **Async SQLAlchemy**: Asynchronous database access with SQLAlchemy 2.0 and `asyncpg`.
- **Alembic Migrations**: Database schema management and versioning.
- **Memory-Efficient Streaming**: Async generators for message consumption to avoid loading entire topics into memory.
- **Structured JSON Logging**: Production-ready logging with `structlog`.
- **RestrictedPython Sandbox**: Secure execution of user-defined enrichment scripts.
- **Messaging Abstraction**: Decoupled messaging layer with a base adapter and Kafka implementation.
- **Versioned API**: API routes are versioned under `/api/v1/`.
- **Dockerized**: Multi-stage Dockerfile for optimized and secure production builds.
- **No Global Mutable State**: Designed for scalability and reliability with multiple workers.

## Project Structure

```
/backend
├── alembic/              → Database migration scripts
├── app/
│   ├── api/              → API route handlers (versioned)
│   │   └── v1/
│   ├── core/             → Config, logging, lifespan manager
│   ├── services/         → Business logic services
│   ├── adapters/         → Messaging abstraction (Kafka)
│   ├── models/           → Pydantic v2 schemas
│   ├── sandbox/          → Script execution sandbox
│   └── db/               → Async SQLAlchemy with Postgres
├── main.py               → Application entry point for Uvicorn
├── requirements.txt      → Python dependencies
├── Dockerfile            → Multi-stage production Dockerfile
├── alembic.ini           → Alembic configuration
└── .env.example          → Environment variable template
```

## Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL database
- Kafka cluster

### 1. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy the environment template and update with your settings:

```bash
cp .env.example .env
```

Edit `.env` with your database and Kafka connection details:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### 4. Run Database Migrations

```bash
alembic upgrade head
```

### 5. Run the Application

```bash
python main.py
```

The API will be available at `http://localhost:8000`.

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Running with Docker

### 1. Build the Docker Image

```bash
docker build -t kafka-replay-backend .
```

### 2. Run the Container

```bash
docker run -d -p 8000:8000 --env-file .env kafka-replay-backend
```

## Key Components

### Async Database Layer

- **SQLAlchemy 2.0**: Asynchronous session management and ORM.
- **Alembic**: Manages database schema migrations.
- **Connection Pooling**: Configurable connection pool for performance.

### Messaging Abstraction

- **Base Adapter**: Defines a common interface for messaging operations.
- **Kafka Adapter**: `aiokafka`-based implementation for async Kafka communication.
- **Memory-Efficient**: Uses `async for` to stream messages without high memory usage.

### Script Sandbox

- **RestrictedPython**: Safely executes untrusted Python code.
- **Timeout Protection**: Prevents long-running scripts from blocking the server.
- **Resource Limits**: (Future) Can be extended to limit memory and CPU usage.

### Structured Logging

- **`structlog`**: Provides context-rich, structured logging.
- **JSON Output**: Configured for JSON log output in production.
- **Uvicorn Integration**: Captures and formats Uvicorn access logs.

## Development

### Running Tests

```bash
pytest
```

### Code Formatting and Linting

- **Black**: `black .`
- **Ruff**: `ruff check .`
- **MyPy**: `mypy .`

## Production Considerations

- **Workers**: The number of Uvicorn workers is configurable via the `WORKERS` environment variable.
- **Security**: The `SECRET_KEY` should be set to a secure, random value in production.
- **Database**: Use a managed PostgreSQL service for reliability and scalability.
- **Kafka**: Use a managed Kafka service or a production-ready cluster.
- **Monitoring**: Integrate with a monitoring solution like Prometheus and Grafana.

## Contributing

Contributions are welcome! Please follow standard Git workflow (fork, branch, PR) workflow.
