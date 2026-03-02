"""
Kafka adapter configuration using Pydantic BaseSettings.

All configuration is sourced from environment variables with sensible defaults.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class KafkaSettings(BaseSettings):
    """Kafka configuration from environment variables."""

    # Broker configuration
    bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Comma-separated list of Kafka brokers",
        alias="KAFKA_BOOTSTRAP_SERVERS",
    )

    # Client configuration
    client_id: str = Field(
        default="replay-tool-backend",
        description="Client ID for Kafka connections",
        alias="KAFKA_CLIENT_ID",
    )

    # Connection pooling
    connections_max_idle_ms: int = Field(
        default=540000,  # 9 minutes
        description="Close idle connections after this many milliseconds",
        alias="KAFKA_CONNECTIONS_MAX_IDLE_MS",
    )

    # Timeouts
    request_timeout_ms: int = Field(
        default=30000,  # 30 seconds
        description="Request timeout in milliseconds",
        alias="KAFKA_REQUEST_TIMEOUT_MS",
    )

    session_timeout_ms: int = Field(
        default=10000,  # 10 seconds
        description="Session timeout for consumer group in milliseconds",
        alias="KAFKA_SESSION_TIMEOUT_MS",
    )

    heartbeat_interval_ms: int = Field(
        default=3000,  # 3 seconds
        description="Heartbeat interval in milliseconds",
        alias="KAFKA_HEARTBEAT_INTERVAL_MS",
    )

    # Consumer configuration
    auto_offset_reset: str = Field(
        default="earliest",
        description="What to do when there is no initial offset (earliest/latest/none)",
        alias="KAFKA_AUTO_OFFSET_RESET",
    )

    enable_auto_commit: bool = Field(
        default=False,
        description="Enable automatic offset commits",
        alias="KAFKA_ENABLE_AUTO_COMMIT",
    )

    auto_commit_interval_ms: int = Field(
        default=5000,  # 5 seconds
        description="Auto commit interval in milliseconds",
        alias="KAFKA_AUTO_COMMIT_INTERVAL_MS",
    )

    max_poll_records: int = Field(
        default=500,
        description="Maximum records to fetch per poll",
        alias="KAFKA_MAX_POLL_RECORDS",
    )

    # Producer configuration
    acks: str = Field(
        default="all",
        description="Producer acks setting (0/1/all)",
        alias="KAFKA_PRODUCER_ACKS",
    )

    retries: int = Field(
        default=3,
        description="Number of retries for producer",
        alias="KAFKA_PRODUCER_RETRIES",
    )

    retry_backoff_ms: int = Field(
        default=100,
        description="Backoff time between retries in milliseconds",
        alias="KAFKA_PRODUCER_RETRY_BACKOFF_MS",
    )

    batch_size: int = Field(
        default=16384,  # 16KB
        description="Producer batch size in bytes",
        alias="KAFKA_PRODUCER_BATCH_SIZE",
    )

    linger_ms: int = Field(
        default=10,
        description="Time to wait for batching in milliseconds",
        alias="KAFKA_PRODUCER_LINGER_MS",
    )

    compression_type: str = Field(
        default="snappy",
        description="Compression type (none/gzip/snappy/lz4/zstd)",
        alias="KAFKA_PRODUCER_COMPRESSION_TYPE",
    )

    # Security configuration
    security_protocol: str = Field(
        default="PLAINTEXT",
        description="Security protocol (PLAINTEXT/SSL/SASL_PLAINTEXT/SASL_SSL)",
        alias="KAFKA_SECURITY_PROTOCOL",
    )

    sasl_mechanism: Optional[str] = Field(
        default=None,
        description="SASL mechanism (PLAIN/SCRAM-SHA-256/SCRAM-SHA-512)",
        alias="KAFKA_SASL_MECHANISM",
    )

    sasl_username: Optional[str] = Field(
        default=None,
        description="SASL username",
        alias="KAFKA_SASL_USERNAME",
    )

    sasl_password: Optional[str] = Field(
        default=None,
        description="SASL password",
        alias="KAFKA_SASL_PASSWORD",
    )

    ssl_cafile: Optional[str] = Field(
        default=None,
        description="Path to CA certificate file",
        alias="KAFKA_SSL_CAFILE",
    )

    ssl_certfile: Optional[str] = Field(
        default=None,
        description="Path to client certificate file",
        alias="KAFKA_SSL_CERTFILE",
    )

    ssl_keyfile: Optional[str] = Field(
        default=None,
        description="Path to client key file",
        alias="KAFKA_SSL_KEYFILE",
    )

    ssl_check_hostname: bool = Field(
        default=True,
        description="Enable SSL hostname checking",
        alias="KAFKA_SSL_CHECK_HOSTNAME",
    )

    # Adapter-specific configuration
    admin_client_pool_size: int = Field(
        default=1,
        description="Number of admin clients to pool",
        alias="KAFKA_ADMIN_CLIENT_POOL_SIZE",
    )

    consumer_pool_size: int = Field(
        default=5,
        description="Number of consumer connections to pool",
        alias="KAFKA_CONSUMER_POOL_SIZE",
    )

    producer_pool_size: int = Field(
        default=5,
        description="Number of producer connections to pool",
        alias="KAFKA_PRODUCER_POOL_SIZE",
    )

    # Replay-specific configuration
    replay_trace_headers_enabled: bool = Field(
        default=True,
        description="Enable replay trace headers in produced messages",
        alias="KAFKA_REPLAY_TRACE_HEADERS_ENABLED",
    )

    replay_source_offset_header: str = Field(
        default="x-replay-source-offset",
        description="Header name for source offset",
        alias="KAFKA_REPLAY_SOURCE_OFFSET_HEADER",
    )

    replay_timestamp_header: str = Field(
        default="x-replay-timestamp",
        description="Header name for replay timestamp",
        alias="KAFKA_REPLAY_TIMESTAMP_HEADER",
    )

    replay_job_id_header: str = Field(
        default="x-replay-job-id",
        description="Header name for replay job ID",
        alias="KAFKA_REPLAY_JOB_ID_HEADER",
    )

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator("bootstrap_servers")
    @classmethod
    def validate_bootstrap_servers(cls, v: str) -> str:
        """Validate bootstrap servers format."""
        if not v or not v.strip():
            raise ValueError("bootstrap_servers cannot be empty")
        return v

    @field_validator("security_protocol")
    @classmethod
    def validate_security_protocol(cls, v: str) -> str:
        """Validate security protocol."""
        valid = {"PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"}
        if v not in valid:
            raise ValueError(f"security_protocol must be one of {valid}")
        return v

    @field_validator("auto_offset_reset")
    @classmethod
    def validate_auto_offset_reset(cls, v: str) -> str:
        """Validate auto offset reset."""
        valid = {"earliest", "latest", "none"}
        if v not in valid:
            raise ValueError(f"auto_offset_reset must be one of {valid}")
        return v

    @field_validator("acks")
    @classmethod
    def validate_acks(cls, v: str) -> str:
        """Validate producer acks."""
        valid = {"0", "1", "all"}
        if v not in valid:
            raise ValueError(f"acks must be one of {valid}")
        return v

    @field_validator("compression_type")
    @classmethod
    def validate_compression_type(cls, v: str) -> str:
        """Validate compression type."""
        valid = {"none", "gzip", "snappy", "lz4", "zstd"}
        if v not in valid:
            raise ValueError(f"compression_type must be one of {valid}")
        return v

    def get_bootstrap_servers_list(self) -> list[str]:
        """Get bootstrap servers as a list."""
        return [s.strip() for s in self.bootstrap_servers.split(",")]

    def get_sasl_config(self) -> dict:
        """Get SASL configuration if enabled."""
        if not self.sasl_mechanism:
            return {}

        return {
            "sasl_mechanism": self.sasl_mechanism,
            "sasl_plain_username": self.sasl_username,
            "sasl_plain_password": self.sasl_password,
        }

    def get_ssl_config(self) -> dict:
        """Get SSL configuration if enabled."""
        if self.security_protocol not in {"SSL", "SASL_SSL"}:
            return {}

        config = {
            "ssl_check_hostname": self.ssl_check_hostname,
        }

        if self.ssl_cafile:
            config["ssl_cafile"] = self.ssl_cafile
        if self.ssl_certfile:
            config["ssl_certfile"] = self.ssl_certfile
        if self.ssl_keyfile:
            config["ssl_keyfile"] = self.ssl_keyfile

        return config
