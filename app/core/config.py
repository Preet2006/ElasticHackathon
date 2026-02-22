"""
Configuration management for CodeJanitor 2.0
Uses Pydantic Settings for robust environment variable handling
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings with environment variable loading
    
    Configuration can be provided via:
    - Environment variables
    - .env file in project root
    - Direct instantiation with parameters
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LLM Configuration
    groq_api_key: str = Field(
        default="",
        description="Groq API key for LLM access"
    )
    
    llm_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Default LLM model to use"
    )
    
    llm_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM responses"
    )
    
    llm_max_retries: int = Field(
        default=3,
        ge=1,
        description="Maximum retry attempts for LLM calls"
    )
    
    # GitHub Configuration
    github_token: str = Field(
        default="",
        description="GitHub personal access token"
    )
    
    # Docker Configuration
    docker_image: str = Field(
        default="python:3.11-slim",
        description="Default Docker image for sandbox execution"
    )
    
    docker_timeout: int = Field(
        default=15,
        ge=1,
        description="Default timeout for Docker execution (seconds)"
    )
    
    docker_memory_limit: str = Field(
        default="512m",
        description="Memory limit for Docker containers"
    )
    
    docker_network_disabled: bool = Field(
        default=True,
        description="Disable network access in Docker containers"
    )
    
    # Elasticsearch (Elastic Cloud)
    es_cloud_id: str = Field(
        default="",
        description="Elastic Cloud deployment Cloud ID"
    )

    es_api_key: str = Field(
        default="",
        description="Elastic Cloud API key (base64-encoded id:key)"
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    log_dir: Path = Field(
        default=Path("logs"),
        description="Directory for log files"
    )
    
    # Project Configuration
    project_name: str = Field(
        default="CodeJanitor 2.0",
        description="Project name"
    )
    
    version: str = Field(
        default="2.0.0",
        description="Application version"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance (singleton pattern)
    
    Returns:
        Settings: The application settings
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Force reload settings from environment
    
    Returns:
        Settings: The reloaded settings
    """
    global _settings
    _settings = Settings()
    return _settings
