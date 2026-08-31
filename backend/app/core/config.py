from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = Field(default="NEXUS", alias="APP_NAME")
    app_env: Literal["development", "test", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_str: str = Field(default="/api/v1", alias="API_V1_STR")
    port: int = Field(default=8000, alias="PORT")
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    redis_url_override: str | None = Field(default=None, alias="REDIS_URL")

    postgres_db: str = Field(default="nexus", alias="POSTGRES_DB")
    postgres_user: str = Field(default="nexus", alias="POSTGRES_USER")
    postgres_password: str = Field(default="nexus", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5433, alias="POSTGRES_PORT")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6380, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_url_override:
            return self.redis_url_override
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    model_config = SettingsConfigDict(
        env_file=[BASE_DIR / ".env", BACKEND_DIR / ".env"],
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
