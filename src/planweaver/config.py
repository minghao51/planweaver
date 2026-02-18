from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional, List
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

    # GitHub Configuration
    github_token: Optional[str] = Field(None, description="GitHub PAT for private repos")

    # Web Search Configuration
    tavily_api_key: Optional[str] = Field(None, description="Tavily API key for web search")
    search_provider: str = Field("tavily", description="Search provider: tavily, serper, duckduckgo")

    # File Upload Configuration
    max_file_size_mb: int = Field(10, description="Maximum file upload size in MB")
    allowed_file_types: List[str] = Field(
        default=[".pdf", ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml"],
        description="Allowed file extensions for upload"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
