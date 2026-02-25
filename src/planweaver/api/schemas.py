import re
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


def sanitize_text(value: str) -> str:
    text = value.strip()
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


class CreateSessionRequest(BaseModel):
    user_intent: str = Field(..., min_length=1, max_length=10000)
    scenario_name: Optional[str] = Field(None, max_length=200)

    @field_validator("user_intent", mode="before")
    @classmethod
    def sanitize_input(cls, value):
        if isinstance(value, str):
            return sanitize_text(value)
        return value


class AnswerQuestionsRequest(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict)

    @field_validator("answers", mode="before")
    @classmethod
    def sanitize_answers(cls, value):
        if isinstance(value, dict):
            return {k: sanitize_text(str(v)) for k, v in value.items()}
        return {}


class ExecutePlanRequest(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)


class GitHubContextRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")


class WebSearchContextRequest(BaseModel):
    query: Optional[str] = Field(
        None,
        description="Search query (optional, auto-generated from intent if not provided)",
    )
