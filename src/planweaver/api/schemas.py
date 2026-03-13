import re
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


def sanitize_text(value: str) -> str:
    text = value.strip()
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


class CreateSessionRequest(BaseModel):
    user_intent: str = Field(
        min_length=1, max_length=5000, description="User's planning intent"
    )
    scenario_name: str = Field(
        default="default",
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9 _-]+$",
        description="Scenario template name",
    )
    planner_model: Optional[str] = Field(
        None, description="Override default planner model"
    )
    executor_model: Optional[str] = Field(
        None, description="Override default executor model"
    )

    @field_validator("user_intent", mode="before")
    @classmethod
    def sanitize_input(cls, value):
        if isinstance(value, str):
            return sanitize_text(value)
        return value


class AnswerQuestionsRequest(BaseModel):
    answers: Dict[str, str] = Field(
        min_length=1, description="List of answers to clarifying questions"
    )

    @field_validator("answers", mode="before")
    @classmethod
    def sanitize_answers(cls, value):
        if isinstance(value, dict):
            return {k: sanitize_text(str(v)) for k, v in value.items()}
        return {}

    @field_validator("answers")
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


class CandidatePlanSchema(BaseModel):
    candidate_id: str
    session_id: Optional[str] = None
    title: str
    summary: str
    source_type: str
    source_model: str
    planning_style: str
    parent_candidate_id: Optional[str] = None
    proposal_id: Optional[str] = None
    status: str
    normalized_plan_id: Optional[str] = None
    normalized_plan: Optional[Dict[str, Any]] = None
    execution_graph: list[Dict[str, Any]] = Field(default_factory=list)
    context_references: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    why_suggested: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CandidatePlanRevisionSchema(BaseModel):
    revision_id: str
    candidate_id: str
    session_id: Optional[str] = None
    revision_type: str
    title: str
    summary: str
    execution_graph: list[Dict[str, Any]] = Field(default_factory=list)
    note: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class PlanningOutcomeSchema(BaseModel):
    outcome_id: str
    session_id: str
    candidate_id: Optional[str] = None
    event_type: str
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class ContextSuggestionSchema(BaseModel):
    id: str
    suggestion_type: str
    title: str
    description: str
    reason: str
    suggested_query: Optional[str] = None
    confidence: float


class CandidateListResponse(BaseModel):
    session_id: str
    selected_candidate_id: Optional[str] = None
    approved_candidate_id: Optional[str] = None
    candidates: list[CandidatePlanSchema]


class CandidateOperationResponse(BaseModel):
    session_id: str
    selected_candidate_id: Optional[str] = None
    approved_candidate_id: Optional[str] = None
    candidate: CandidatePlanSchema
    execution_graph: list[Dict[str, Any]] = Field(default_factory=list)
    status: str


class CandidateOutcomesResponse(BaseModel):
    session_id: str
    outcomes: list[PlanningOutcomeSchema]


class RefineCandidateRequest(BaseModel):
    operation: str = Field(
        ...,
        description="One of edit_step, delete_step, add_step, regenerate_from_step",
    )
    step_id: Optional[int] = Field(default=None, ge=1)
    task: Optional[str] = Field(default=None, max_length=2000)
    insert_after_step_id: Optional[int] = Field(default=None, ge=1)
    note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("operation", mode="before")
    @classmethod
    def sanitize_operation(cls, value):
        if isinstance(value, str):
            return sanitize_text(value)
        return value

    @field_validator("task", "note", mode="before")
    @classmethod
    def sanitize_optional_text(cls, value):
        if isinstance(value, str):
            cleaned = sanitize_text(value)
            return cleaned or None
        return value


class BranchCandidateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("title", "note", mode="before")
    @classmethod
    def sanitize_branch_text(cls, value):
        if isinstance(value, str):
            cleaned = sanitize_text(value)
            return cleaned or None
        return value


# ==================== Optimizer Schemas ====================


class OptimizerRequest(BaseModel):
    session_id: Optional[str] = Field(
        default=None, min_length=1, description="Session identifier"
    )
    candidate_id: Optional[str] = Field(
        default=None, min_length=1, description="Selected candidate ID to optimize"
    )
    selected_proposal_id: Optional[str] = Field(
        default=None, min_length=1, description="Legacy selected proposal ID"
    )
    optimization_types: list[str] = Field(
        default=["simplified", "enhanced"], description="Types of variants to generate"
    )
    user_context: Optional[str] = Field(
        None, max_length=2000, description="Additional context from user"
    )

    @field_validator("optimization_types")
    @classmethod
    def validate_types(cls, v):
        valid_types = {"simplified", "enhanced", "cost-optimized"}
        if not set(v).issubset(valid_types):
            raise ValueError(f"Invalid types. Must be subset of: {valid_types}")
        return v

    @field_validator("candidate_id", "selected_proposal_id")
    @classmethod
    def sanitize_candidate_values(cls, value):
        if isinstance(value, str):
            cleaned = sanitize_text(value)
            return cleaned or None
        return value


class OptimizedVariantSchema(BaseModel):
    id: str
    parent_candidate_id: Optional[str] = None
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
        description="Models to use for rating",
    )
    criteria: list[str] = Field(
        default=["feasibility", "cost_efficiency", "time_efficiency", "complexity"],
        description="Rating criteria",
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
    rationale: Optional[str] = Field(
        None, max_length=2000, description="Rating rationale"
    )

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


class NormalizedStepSchema(BaseModel):
    step_id: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    validation: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    owner_model: Optional[str] = None
    estimated_time_minutes: Optional[int] = None


class ManualPlanRequest(BaseModel):
    session_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    summary: str = Field(default="", max_length=2000)
    plan_text: Optional[str] = Field(None, max_length=10000)
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    fallbacks: list[str] = Field(default_factory=list)
    steps: list[NormalizedStepSchema] = Field(default_factory=list)
    estimated_time_minutes: Optional[int] = Field(default=None, ge=0)
    estimated_cost_usd: Optional[Decimal] = Field(default=None, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    judge_models: list[str] = Field(default_factory=list)


class NormalizePlanRequest(BaseModel):
    session_id: Optional[str] = None
    plan: Dict[str, Any]
    source_type: str = Field(default="llm_generated")
    source_model: str = Field(default="unknown", min_length=1)
    planning_style: str = Field(default="baseline", min_length=1)
    persist: bool = True


class PlanEvaluationRequest(BaseModel):
    session_id: Optional[str] = None
    plans: list[Dict[str, Any]] = Field(min_length=1)
    judge_models: list[str] = Field(default_factory=list)


class PairwiseComparisonRequest(BaseModel):
    session_id: Optional[str] = None
    plans: list[Dict[str, Any]] = Field(min_length=2, max_length=10)
    judge_models: list[str] = Field(default_factory=list)


class NormalizedPlanSchema(BaseModel):
    id: str
    session_id: Optional[str] = None
    source_type: str
    source_model: str
    planning_style: str
    title: str
    summary: str
    assumptions: list[str]
    constraints: list[str]
    success_criteria: list[str]
    risks: list[str]
    fallbacks: list[str]
    estimated_time_minutes: Optional[int] = None
    estimated_cost_usd: Optional[Decimal] = None
    steps: list[NormalizedStepSchema]
    metadata: Dict[str, Any]
    normalization_warnings: list[str]


class PlanEvaluationSchema(BaseModel):
    plan_id: str
    judge_model: str
    rubric_scores: Dict[str, float]
    overall_score: float
    strengths: list[str]
    weaknesses: list[str]
    blocking_issues: list[str]
    confidence: float
    verdict: str


class PairwiseComparisonSchema(BaseModel):
    left_plan_id: str
    right_plan_id: str
    judge_model: str
    winner_plan_id: str
    margin: str
    rationale: str
    preference_factors: list[str]


class RankedPlanSchema(BaseModel):
    plan_id: str
    final_score: float
    rank: int
    confidence: float
    disagreement_level: str
    recommendation_reason: str


class ManualPlanResponse(BaseModel):
    normalized_plan: NormalizedPlanSchema
    evaluations: Dict[str, PlanEvaluationSchema]
    ranking: list[RankedPlanSchema]


class NormalizePlanResponse(BaseModel):
    normalized_plan: NormalizedPlanSchema


class PlanEvaluationResponse(BaseModel):
    normalized_plans: list[NormalizedPlanSchema]
    evaluations: Dict[str, Dict[str, PlanEvaluationSchema]]
    ranking: list[RankedPlanSchema]


class PairwiseComparisonResponse(BaseModel):
    normalized_plans: list[NormalizedPlanSchema]
    evaluations: Dict[str, Dict[str, PlanEvaluationSchema]]
    comparisons: list[PairwiseComparisonSchema]
    ranking: list[RankedPlanSchema]
