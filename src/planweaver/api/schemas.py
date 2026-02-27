import re
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


def sanitize_text(value: str) -> str:
    text = value.strip()
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


class CreateSessionRequest(BaseModel):
    user_intent: str = Field(
        min_length=1,
        max_length=5000,
        description="User's planning intent"
    )
    scenario_name: str = Field(
        default="default",
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9 _-]+$",
        description="Scenario template name"
    )
    planner_model: Optional[str] = Field(
        None,
        description="Override default planner model"
    )
    executor_model: Optional[str] = Field(
        None,
        description="Override default executor model"
    )

    @field_validator("user_intent", mode="before")
    @classmethod
    def sanitize_input(cls, value):
        if isinstance(value, str):
            return sanitize_text(value)
        return value


class AnswerQuestionsRequest(BaseModel):
    answers: Dict[str, str] = Field(
        min_length=1,
        description="List of answers to clarifying questions"
    )

    @field_validator("answers", mode="before")
    @classmethod
    def sanitize_answers(cls, value):
        if isinstance(value, dict):
            return {k: sanitize_text(str(v)) for k, v in value.items()}
        return {}

    @field_validator('answers')
    @classmethod
    def validate_answer_length(cls, v: Dict[str, str]) -> Dict[str, str]:
        for key, answer in v.items():
            if len(answer) > 2000:
                raise ValueError(f"Answer '{key}' exceeds 2000 characters")
        return v


class ExecutePlanRequest(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)


class GitHubContextRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")


class WebSearchContextRequest(BaseModel):
    query: Optional[str] = Field(
        None,
        description="Search query (optional, auto-generated from intent if not provided)",
    )


# ==================== Optimizer Schemas ====================

class OptimizerRequest(BaseModel):
    selected_proposal_id: str = Field(..., min_length=10, description="Selected proposal ID to optimize")
    optimization_types: list[str] = Field(
        default=["simplified", "enhanced"],
        description="Types of variants to generate"
    )
    user_context: Optional[str] = Field(None, max_length=2000, description="Additional context from user")

    @field_validator("optimization_types")
    @classmethod
    def validate_types(cls, v):
        valid_types = {"simplified", "enhanced", "cost-optimized"}
        if not set(v).issubset(valid_types):
            raise ValueError(f"Invalid types. Must be subset of: {valid_types}")
        return v


class OptimizedVariantSchema(BaseModel):
    id: str
    proposal_id: str
    variant_type: str
    execution_graph: list[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: Optional[str] = None


class OptimizerResponse(BaseModel):
    optimization_id: str
    status: str
    variants: list[OptimizedVariantSchema]
    ratings: Dict[str, Any]
    session_id: str


class RatePlansRequest(BaseModel):
    plan_ids: list[str] = Field(..., min_length=1, description="Plan IDs to rate")
    models: list[str] = Field(
        default=["claude-3.5-sonnet", "gpt-4o", "deepseek-chat"],
        description="Models to use for rating"
    )
    criteria: list[str] = Field(
        default=["feasibility", "cost_efficiency", "time_efficiency", "complexity"],
        description="Rating criteria"
    )


class ModelRatingSchema(BaseModel):
    model_name: str
    ratings: Dict[str, float]
    overall_score: float
    reasoning: str


class PlanRatingsSchema(BaseModel):
    plan_id: str
    ratings: Dict[str, ModelRatingSchema]
    average_score: float


class RatePlansResponse(BaseModel):
    rating_id: str
    status: str
    ratings: Dict[str, PlanRatingsSchema]


class UserRatingRequest(BaseModel):
    plan_id: str = Field(..., min_length=10, description="Plan ID to rate")
    rating: int = Field(..., ge=1, le=5, description="User rating 1-5")
    comment: Optional[str] = Field(None, max_length=1000, description="User comment")
    rationale: Optional[str] = Field(None, max_length=2000, description="Rating rationale")

    @field_validator("comment", "rationale", mode="before")
    @classmethod
    def sanitize_text_input(cls, value):
        if isinstance(value, str):
            return sanitize_text(value)
        return value


class UserRatingResponse(BaseModel):
    saved: bool
    rating_id: str


class OptimizationStateResponse(BaseModel):
    status: str  # "idle", "generating_variants", "rating", "completed", "error"
    progress: float = 0.0  # 0.0 to 1.0
    message: Optional[str] = None
