from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://geo:geo@postgres:5432/geo"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_secure: bool = False
    minio_quarantine_bucket: str = "geo-quarantine"
    minio_clean_bucket: str = "geo-clean"
    clamav_host: str = "clamav"
    clamav_port: int = 3310
    scan_timeout_seconds: int = 120
    max_upload_size_mb: int = 25
    max_archive_uncompressed_mb: int = 100
    max_archive_files: int = 100
    max_features: int = 50000
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings():
    return Settings()
