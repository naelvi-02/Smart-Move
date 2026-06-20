"""
Configuration settings using Pydantic.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache

from runtime_config import get_env_file


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openrouter_api_key: str = ""
    novita_api_key: str = ""
    civitai_api_key: str = ""
    admin_password: str = "admin123"
    
    # Database
    database_url: str = "sqlite:///./smart_move.db"
    
    # API Base URLs
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    novita_base_url: str = "https://api.novita.ai/v3"
    civitai_base_url: str = "https://civitai.com/api/v1"
    civitai_nsfw_base_url: str = "https://civitai.red/api/v1"
    
    class Config:
        env_file = str(get_env_file())
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
