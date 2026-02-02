"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/third_space"
    test_database_url: str = "postgresql+asyncpg://test:test@localhost:5433/third_space_test"

    # Security secrets
    secret_key: str = "dev-secret-key-change-in-production"
    api_key_secret: str = "dev-api-key-secret-change-in-production"
    jwt_secret: str = "dev-jwt-secret-change-in-production"

    # JWT settings
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Rate limiting
    register_rate_limit: str = "5/hour"
    login_rate_limit: str = "10/15minutes"
    api_key_create_rate_limit: str = "10/hour"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins, filtering empty strings."""
        if not self.cors_origins:
            return ["http://localhost:3000"]
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins if origins else ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
