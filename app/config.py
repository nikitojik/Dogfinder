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

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    ml_lazy_load: bool = False

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "DogFinder <noreply@dogfinder.local>"
    smtp_tls: bool = False

    base_url: str = "http://localhost:8000"
    notifications_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
