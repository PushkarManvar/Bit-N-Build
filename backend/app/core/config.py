from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://journeylens:journeylens_dev_only@db:5432/journeylens"
    cors_origins: str = "http://localhost:3000"
    llm_primary_base_url: str | None = None
    llm_primary_api_key: str | None = None
    llm_primary_model: str | None = None
    llm_backup_base_url: str | None = None
    llm_backup_api_key: str | None = None
    llm_backup_model: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
