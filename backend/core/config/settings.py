"""
Application settings using Pydantic v2 with pydantic-settings.

This module provides centralized configuration management for the application,
supporting different environments (development, production) with secure
handling of secrets and environment variables.
"""

import secrets
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    Uses pydantic-settings for automatic loading from environment variables
    and .env files with validation and type conversion.
    """
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    # Application
    app_name: str = "Aionix Agent Backend"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    secret_key: str = secrets.token_urlsafe(32)

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/aionix_agent"

    # API Keys
    openai_api_key: str = ""
    news_api_key: str = ""
    alpha_vantage_api_key: str = ""
    vector_db_api_key: str = ""
    serpapi_api_key: str = ""

    # Security
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # CORS
    cors_origins: List[AnyHttpUrl] = []

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, List[str]]
    ) -> Union[List[str], str]:
        """Parse CORS origins from environment variable."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # File Upload
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = [".pdf", ".docx", ".txt"]
    upload_directory: str = "uploads"

    # External APIs
    news_api_base_url: str = "https://newsapi.org/v2"
    alpha_vantage_base_url: str = "https://www.alphavantage.co/query"
    openai_base_url: str = "https://api.openai.com/v1"

    # Rate Limiting
    news_api_rate_limit: int = 100  # requests per day
    alpha_vantage_rate_limit: int = 25  # requests per day

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Health Checks
    health_check_interval: int = 60  # seconds

    # AI Engine Configuration
    default_llm_provider: str = "openai"
    default_openai_model: str = "gpt-4"
    default_huggingface_model: str = "meta-llama/Llama-2-7b-chat-hf"
    huggingface_api_key: str = ""

    # Vector Database Configuration
    vector_db_provider: str = "pinecone"  # pinecone or weaviate
    pinecone_api_key: str = ""
    pinecone_index_name: str = "aionix-documents"
    weaviate_url: str = "http://localhost:8080"
    weaviate_class_name: str = "Document"

    # Embedding Configuration
    embedding_provider: str = "openai"  # openai or huggingface
    embedding_model: str = "text-embedding-3-small"

    # Document Processing Configuration
    max_chunk_size: int = 2000  # tokens
    chunk_overlap: int = 200  # tokens
    chunking_strategy: str = "token_aware"  # fixed_size, sentence_aware, token_aware

    # Memory Configuration
    enable_memory: bool = True
    memory_retention_days: int = 365

    # Background Tasks
    enable_celery: bool = False
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_db: int = 0
    redis_max_connections: int = 20

    # Task Scheduler Configuration
    scheduler_cleanup_days: int = 30  # Days to keep execution history
    max_concurrent_tasks: int = 5  # Maximum concurrent task executions
    task_timeout_seconds: int = 3600  # 1 hour timeout for tasks

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def database_echo(self) -> bool:
        """Enable SQLAlchemy query logging in development."""
        return self.is_development and self.debug


# Create global settings instance
settings = Settings()


# Environment-specific settings validation
def validate_settings() -> None:
    """
    Validate settings based on environment requirements.

    Raises:
        ValueError: If required settings are missing for production
    """
    if settings.is_production:
        required_keys = [
            "database_url",
            "secret_key",
            "openai_api_key",
            "news_api_key",
            "alpha_vantage_api_key",
            "vector_db_api_key",
            "serpapi_api_key",
        ]

        missing_keys = []
        for key in required_keys:
            value = getattr(settings, key, "")
            if not value or str(value).startswith("your_"):
                missing_keys.append(key)

        if missing_keys:
            raise ValueError(
                f"Missing required production settings: {', '.join(missing_keys)}. "
                "Please set these in your environment variables or .env file."
            )

    # Validate database URL format
    if not settings.database_url.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
        raise ValueError(
            "DATABASE_URL must be a valid PostgreSQL or SQLite async URL"
        )


# Run validation on import
validate_settings()
