from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and configuration loaded from environment variables."""

    DATABASE_URL: str
    MONGO_URI: str
    MONGO_DB: str = "leaderboard"
    REDIS_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC_SCORE_UPDATES: str = "score.updates"
    SQS_QUEUE_URL: str
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"
    AWS_DEFAULT_REGION: str = "us-east-1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Modern Pydantic V2 configuration:
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",  # Prevents errors if extra variables exist in .env
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()