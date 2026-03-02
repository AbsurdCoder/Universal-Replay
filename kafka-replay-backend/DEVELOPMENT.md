# Development Guide

## Local Development Setup

### 1. Clone and Setup

```bash
git clone <repository>
cd kafka-replay-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Dependencies with Docker Compose

Create a `docker-compose.yml` in the project root:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: replay_user
      POSTGRES_PASSWORD: replay_password
      POSTGRES_DB: replay_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    ports:
      - "2181:2181"

volumes:
  postgres_data:
```

Start services:

```bash
docker-compose up -d
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Update `.env`:

```env
DATABASE_URL=postgresql+asyncpg://replay_user:replay_password@localhost:5432/replay_db
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start Development Server

```bash
python main.py
```

Access the API at `http://localhost:8000/docs`.

## Creating a New Migration

```bash
alembic revision --autogenerate -m "Add new column"
alembic upgrade head
```

## Writing Services

Services encapsulate business logic and should:

1. Accept dependencies through the constructor
2. Use async/await for I/O operations
3. Raise appropriate exceptions
4. Log operations with context

Example:

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

class MyService:
    def __init__(self, kafka_adapter: KafkaAdapter, session: AsyncSession):
        self.kafka = kafka_adapter
        self.session = session

    async def do_something(self, param: str) -> str:
        logger.info("Doing something", param=param)
        try:
            result = await self.kafka.list_topics()
            logger.info("Got topics", count=len(result))
            return result[0] if result else None
        except Exception as e:
            logger.error("Failed to do something", error=str(e))
            raise
```

## Writing API Endpoints

Endpoints should:

1. Use dependency injection for services
2. Validate input with Pydantic models
3. Handle errors gracefully
4. Return appropriate HTTP status codes

Example:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/items/{item_id}")
async def get_item(
    item_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> ItemResponse:
    try:
        service = ItemService(session)
        item = await service.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item
    except Exception as e:
        logger.error("Failed to get item", item_id=item_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Writing Enrichment Scripts

Enrichment scripts must define an `enrich(message)` function:

```python
# Example enrichment script
def enrich(message):
    """Add timestamp to message."""
    import json
    from datetime import datetime
    
    if isinstance(message, dict):
        message['enriched_at'] = datetime.utcnow().isoformat()
    
    return message
```

Register and use:

```python
script_service = ScriptService()
await script_service.register_script("add_timestamp", script_code)
enriched = await script_service.enrich_message("add_timestamp", {"data": "value"})
```

## Testing

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services import ReplayService

@pytest.mark.asyncio
async def test_create_job():
    session = AsyncMock()
    service = ReplayService(session)
    
    request = CreateReplayJobRequest(
        name="Test Job",
        source_topic="input",
        target_topic="output",
    )
    
    result = await service.create_job(request)
    
    assert result.name == "Test Job"
    assert result.status == ReplayJobStatus.PENDING
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_replay_job_workflow(kafka_adapter, session):
    # Create job
    service = ReplayService(session)
    job = await service.create_job(request)
    
    # Verify job in database
    retrieved = await service.get_job(job.job_id)
    assert retrieved.job_id == job.job_id
```

### Running Tests

```bash
pytest                    # Run all tests
pytest -v               # Verbose output
pytest -k test_name     # Run specific test
pytest --cov            # With coverage report
pytest -m asyncio       # Run async tests
```

## Code Quality

### Formatting

```bash
black .
```

### Linting

```bash
ruff check .
ruff check . --fix
```

### Type Checking

```bash
mypy .
```

### All Together

```bash
black . && ruff check . --fix && mypy . && pytest
```

## Debugging

### Enable Debug Logging

```bash
LOG_LEVEL=DEBUG python main.py
```

### Using Debugger

```python
import pdb; pdb.set_trace()  # Breakpoint
```

### Inspect Database

```bash
psql -U replay_user -d replay_db -h localhost
```

## Common Tasks

### Create a New API Endpoint

1. Create request/response models in `app/models/schemas.py`
2. Add service method in `app/services/`
3. Create route in `app/api/v1/`
4. Add tests in `tests/`

### Add a Database Field

1. Update model in `app/db/models.py`
2. Create migration: `alembic revision --autogenerate -m "Add field"`
3. Review and run migration: `alembic upgrade head`

### Register an Enrichment Script

```python
script_code = """
def enrich(message):
    message['processed'] = True
    return message
"""

script_service = ScriptService()
await script_service.register_script("my_script", script_code)
```

## Performance Tips

1. **Use Async Generators**: Stream large datasets instead of loading into memory.
2. **Connection Pooling**: Configure appropriate pool size for your workload.
3. **Batch Operations**: Process messages in batches for better throughput.
4. **Indexing**: Ensure frequently queried fields are indexed.
5. **Monitoring**: Use structured logging to identify bottlenecks.

## Troubleshooting

### Database Connection Issues

```
Error: could not translate host name "localhost" to address
```

Ensure PostgreSQL is running and accessible:

```bash
docker-compose ps
docker-compose logs postgres
```

### Kafka Connection Issues

```
Error: NoBrokersAvailable
```

Ensure Kafka is running:

```bash
docker-compose logs kafka
```

### Migration Issues

```
Error: Can't locate revision identified by 'abc123'
```

Check migration history:

```bash
alembic history
alembic current
```

Reset if needed:

```bash
alembic downgrade base
alembic upgrade head
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [aiokafka Documentation](https://aiokafka.readthedocs.io/)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
- [RestrictedPython](https://restrictedpython.readthedocs.io/)
