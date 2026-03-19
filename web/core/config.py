"""
Configuration management for Scholia Web Backend.
Loads settings from environment variables and .env file.
"""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.

    Required settings:
    - ANTHROPIC_API_KEY: API key for Claude

    Optional settings:
    - GOOGLE_API_KEY: For Gemini models
    - DATABASE_URL: PostgreSQL connection string (defaults to local)
    - NOTION_CLIENT_ID, NOTION_CLIENT_SECRET, NOTION_REDIRECT_URI: For Notion OAuth
    """

    # Required settings
    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude",
        validation_alias="ANTHROPIC_API_KEY"
    )

    database_url: str = Field(
        default="postgresql://scholia:scholia@localhost:5432/scholia",
        description="PostgreSQL connection string (e.g., postgres://user:pass@host/db)",
        validation_alias="DATABASE_URL"
    )

    # Optional Google/Gemini settings
    google_api_key: Optional[str] = Field(
        default=None,
        description="Google API key for Gemini models (optional)",
        validation_alias="GOOGLE_API_KEY"
    )

    # Notion OAuth settings (optional)
    notion_client_id: Optional[str] = Field(
        default=None,
        description="Notion OAuth Client ID",
        validation_alias="NOTION_CLIENT_ID"
    )

    notion_client_secret: Optional[str] = Field(
        default=None,
        description="Notion OAuth Client Secret",
        validation_alias="NOTION_CLIENT_SECRET"
    )

    notion_redirect_uri: str = Field(
        default="http://localhost:8000/api/notion/callback",
        description="Notion OAuth redirect URI",
        validation_alias="NOTION_REDIRECT_URI"
    )

    # Base URL for OAuth callbacks (e.g., https://myapp.com or http://localhost:8000)
    base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for OAuth callbacks",
        validation_alias="BASE_URL"
    )

    # Application settings
    app_name: str = Field(
        default="Scholia",
        description="Application name"
    )

    debug: bool = Field(
        default=False,
        description="Enable debug mode",
        validation_alias="DEBUG"
    )

    # Model configuration for pydantic-settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_anthropic_key(cls, v: str) -> str:
        """Validate that Anthropic API key is provided and non-empty."""
        if not v or not v.strip():
            raise ValueError("ANTHROPIC_API_KEY is required and cannot be empty")
        return v.strip()

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate PostgreSQL connection string."""
        if not v or not v.strip():
            raise ValueError("DATABASE_URL cannot be empty")
        v = v.strip()
        # Render uses postgres:// but asyncpg expects postgresql://
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://", 1)
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    def has_gemini_config(self) -> bool:
        """Check if Gemini is properly configured."""
        return bool(self.google_api_key)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance (singleton pattern).

    Returns:
        Settings: Application settings
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience function for dependency injection in FastAPI
def get_settings_dependency() -> Settings:
    """FastAPI dependency for injecting settings."""
    return get_settings()
