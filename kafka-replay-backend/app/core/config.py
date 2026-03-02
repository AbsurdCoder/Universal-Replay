"""Application configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP_ID: str = "kafka-replay-tool"
    KAFKA_CONSUMER_TIMEOUT_MS: int = 5000
    KAFKA_BATCH_SIZE: int = 100

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://replay_user:replay_password@localhost:5432/replay_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_RECYCLE: int = 3600

    # Logging
    LOG_FORMAT: str = "json"
    STRUCTLOG_LEVEL: str = "info"

    # Script Sandbox
    SCRIPT_EXECUTION_TIMEOUT: int = 30
    SCRIPT_MAX_MEMORY_MB: int = 256

    # Security
    SECRET_KEY: str = "change-me-in-production"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
