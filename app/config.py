from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/splitwise",
    )

    # Auth
    secret_key: str = Field(default="change-me-in-production")
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    github_client_id: str = Field(default="")
    github_client_secret: str = Field(default="")

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")

    # Storage
    storage_dir: str = Field(default="./storage")


settings = Settings()
