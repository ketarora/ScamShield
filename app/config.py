"""
Configuration for ScamShield, loaded from environment variables.
Copy .env.example to .env and fill in real values before running.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # WhatsApp Cloud API (from Meta for Developers)
    whatsapp_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str
    whatsapp_app_secret: str

    # LLM
    anthropic_api_key: str
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # Database
    database_url: str

    # Misc
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
