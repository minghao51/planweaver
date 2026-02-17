from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "extra": "ignore"}

    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    default_planner_model: str = "gemini-2.5-flash"
    default_executor_model: str = "gemini-3-flash"
    database_url: str = "sqlite:///./planweaver.db"
    cors_origins: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
