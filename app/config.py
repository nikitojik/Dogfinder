from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    debug: bool = True

    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "pet-photos"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
