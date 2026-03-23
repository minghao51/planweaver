from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from datetime import datetime, timezone
from decimal import Decimal
import uuid


class PlanStatus(str, Enum):
    BRAINSTORMING = "BRAINSTORMING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Constraint(BaseModel):
    key: str
    value: Any
    locked: bool = False


class LockedConstraints(BaseModel):
    constraints: Dict[str, Any] = Field(default_factory=dict)


class OpenQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    answered: bool = False
    answer: Optional[str] = None
    rationale: Optional[str] = None
    context_references: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None


class StrawmanProposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    selected: bool = False
    why_suggested: Optional[str] = None
    context_references: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    planning_style: str = "baseline"
    parent_candidate_id: Optional[str] = None


class ProposalWithAnalysis(BaseModel):
    """Proposal with lightweight analysis for quick comparison"""

    # Existing fields from StrawmanProposal
    proposal_id: str
    title: str
    description: str
    pros: List[str]
    cons: List[str]
    selected: bool = False

    # New lightweight analysis fields
    estimated_step_count: int
    complexity_score: Literal["Low", "Medium", "High"]
    estimated_time_minutes: int
    estimated_cost_usd: Decimal
    risk_factors: List[str]

    class Config:
        from_attributes = True


class PreconditionAnnotation(BaseModel):
    precondition_type: str
    check_expression: str
    probe_result: Optional[bool] = None
    probe_error: Optional[str] = None


class ExecutionStep(BaseModel):
    step_id: int
    task: str
    prompt_template_id: str
    assigned_model: str
    status: StepStatus = StepStatus.PENDING
    dependencies: List[int] = Field(default_factory=list)
    output: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    preconditions: List[PreconditionAnnotation] = Field(default_factory=list)


class ExternalContext(BaseModel):
    """External context source for planning enhancement"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: Literal["github", "web_search", "file_upload"]
    source_url: Optional[str] = None
    content_summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Plan(BaseModel):
    session_id: str = Field(default_factory=lambda: f"proj_{uuid.uuid4().hex[:6]}")
    status: PlanStatus = PlanStatus.BRAINSTORMING
    user_intent: str
    scenario_name: Optional[str] = None
    locked_constraints: Dict[str, Any] = Field(default_factory=dict)
    open_questions: List[OpenQuestion] = Field(default_factory=list)
    strawman_proposals: List[StrawmanProposal] = Field(default_factory=list)
    execution_graph: List[ExecutionStep] = Field(default_factory=list)
    external_contexts: List[ExternalContext] = Field(
        default_factory=list,
        description="External context sources for enhanced planning",
    )
    candidate_plans: List[CandidatePlan] = Field(default_factory=list)
    candidate_revisions: List[CandidatePlanRevision] = Field(default_factory=list)
    planning_outcomes: List[PlanningOutcome] = Field(default_factory=list)
    context_suggestions: List[ContextSuggestion] = Field(default_factory=list)
    selected_candidate_id: Optional[str] = None
    approved_candidate_id: Optional[str] = None
    planner_model: Optional[str] = Field(default=None, description="User-selected planner model override")
    executor_model: Optional[str] = Field(default=None, description="Executor model to use for this plan")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the plan")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    final_output: Optional[Any] = None

    def add_open_question(self, question: str) -> None:
        self.open_questions.append(OpenQuestion(question=question))
        self.updated_at = datetime.now(timezone.utc)

    def lock_constraint(self, key: str, value: Any) -> None:
        self.locked_constraints[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def add_step(self, step: ExecutionStep) -> None:
        self.execution_graph.append(step)
        self.updated_at = datetime.now(timezone.utc)

    def get_pending_steps(self) -> List[ExecutionStep]:
        return [s for s in self.execution_graph if s.status == StepStatus.PENDING]

    def get_proposal_by_id(self, proposal_id: str) -> StrawmanProposal:
        """Get proposal by ID."""
        for prop in self.strawman_proposals:
            if prop.id == proposal_id:
                return prop
        raise ValueError(f"Proposal {proposal_id} not found")

    def get_candidate_by_id(self, candidate_id: str) -> CandidatePlan:
        for candidate in self.candidate_plans:
            if candidate.candidate_id == candidate_id:
                return candidate
        raise ValueError(f"Candidate {candidate_id} not found")

    def upsert_candidate(self, candidate: CandidatePlan) -> CandidatePlan:
        candidate.updated_at = datetime.now(timezone.utc)
        for index, existing in enumerate(self.candidate_plans):
            if existing.candidate_id == candidate.candidate_id:
                self.candidate_plans[index] = candidate
                self.updated_at = datetime.now(timezone.utc)
                return candidate
        self.candidate_plans.append(candidate)
        self.updated_at = datetime.now(timezone.utc)
        return candidate

    def record_candidate_revision(self, revision: CandidatePlanRevision) -> None:
        self.candidate_revisions.append(revision)
        self.updated_at = datetime.now(timezone.utc)

    def record_outcome(self, outcome: PlanningOutcome) -> None:
        self.planning_outcomes.append(outcome)
        self.updated_at = datetime.now(timezone.utc)


class StepSummary(BaseModel):
    """Simplified step for comparison display"""

    task: str
    complexity: Literal["Low", "Medium", "High"]
    estimated_time_minutes: int


class ProposalDetail(BaseModel):
    """Full proposal with execution graph for comparison"""

    proposal_id: str
    full_execution_graph: List[ExecutionStep]
    accurate_time_estimate: int
    accurate_cost_estimate: Decimal
    all_risk_factors: List[str]
    generation_error: Optional[str] = None


class ProposalComparison(BaseModel):
    """Detailed comparison of selected proposals"""

    session_id: str
    proposals: List[ProposalDetail]
    common_steps: List[StepSummary]
    unique_steps_by_proposal: Dict[str, List[StepSummary]]
    time_comparison: Dict[str, int]
    cost_comparison: Dict[str, Decimal]
    complexity_comparison: Dict[str, str]


class ComparisonRequest(BaseModel):
    """Request to compare proposals"""

    proposal_ids: List[str] = Field(
        min_length=2,
        max_length=10,
        description="List of proposal IDs to compare (2-10)",
    )


class PlanSourceType(str, Enum):
    LLM_GENERATED = "llm_generated"
    MANUAL = "manual"
    OPTIMIZED_VARIANT = "optimized_variant"


class CandidatePlanStatus(str, Enum):
    DRAFT = "draft"
    SELECTED = "selected"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class EvaluationVerdict(str, Enum):
    STRONG = "strong"
    ACCEPTABLE = "acceptable"
    WEAK = "weak"
    REJECT = "reject"


class DisagreementLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ComparisonMargin(str, Enum):
    NARROW = "narrow"
    MODERATE = "moderate"
    CLEAR = "clear"


class NormalizedStep(BaseModel):
    step_id: str
    description: str
    dependencies: List[str] = Field(default_factory=list)
    validation: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    owner_model: Optional[str] = None
    estimated_time_minutes: Optional[int] = None


class NormalizedPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    source_type: PlanSourceType
    source_model: str
    planning_style: str = "baseline"
    title: str
    summary: str
    assumptions: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    fallbacks: List[str] = Field(default_factory=list)
    estimated_time_minutes: Optional[int] = None
    estimated_cost_usd: Optional[Decimal] = None
    steps: List[NormalizedStep] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    normalization_warnings: List[str] = Field(default_factory=list)


class PlanEvaluation(BaseModel):
    plan_id: str
    judge_model: str
    rubric_scores: Dict[str, float]
    overall_score: float
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    blocking_issues: List[str] = Field(default_factory=list)
    confidence: float
    verdict: EvaluationVerdict


class PairwisePlanComparison(BaseModel):
    left_plan_id: str
    right_plan_id: str
    judge_model: str
    winner_plan_id: str
    margin: ComparisonMargin
    rationale: str
    preference_factors: List[str] = Field(default_factory=list)


class RankedPlanResult(BaseModel):
    plan_id: str
    final_score: float
    rank: int
    confidence: float
    disagreement_level: DisagreementLevel
    recommendation_reason: str


class ManualPlanSubmission(BaseModel):
    session_id: Optional[str] = None
    title: str
    summary: str = ""
    plan_text: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    fallbacks: List[str] = Field(default_factory=list)
    steps: List[NormalizedStep] = Field(default_factory=list)
    estimated_time_minutes: Optional[int] = None
    estimated_cost_usd: Optional[Decimal] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidatePlan(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    title: str
    summary: str
    source_type: PlanSourceType
    source_model: str
    planning_style: str = "baseline"
    parent_candidate_id: Optional[str] = None
    proposal_id: Optional[str] = None
    status: CandidatePlanStatus = CandidatePlanStatus.DRAFT
    normalized_plan_id: Optional[str] = None
    normalized_plan: Optional[Dict[str, Any]] = None
    execution_graph: List[ExecutionStep] = Field(default_factory=list)
    context_references: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    why_suggested: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CandidatePlanRevision(BaseModel):
    revision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    candidate_id: str
    session_id: Optional[str] = None
    revision_type: str
    title: str
    summary: str
    execution_graph: List[ExecutionStep] = Field(default_factory=list)
    note: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlanningOutcome(BaseModel):
    outcome_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    candidate_id: Optional[str] = None
    event_type: str
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContextSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    suggestion_type: Literal["github", "web_search", "file_upload"]
    title: str
    description: str
    reason: str
    suggested_query: Optional[str] = None
    confidence: float = 0.5


class IntentAnalysis(BaseModel):
    identified_constraints: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    suggested_approach: str = ""
    estimated_complexity: Literal["low", "medium", "high"] = "medium"


class ProposalAnalysisEntry(BaseModel):
    estimated_step_count: int = 5
    complexity_score: Literal["Low", "Medium", "High"] = "Medium"
    estimated_time_minutes: int = 10
    estimated_cost_usd: float = 0.005
    risk_factors: List[str] = Field(default_factory=list)


class ProposalAnalysis(BaseModel):
    proposals: Dict[str, ProposalAnalysisEntry] = Field(default_factory=dict)


class StrawmanProposalInput(BaseModel):
    title: str
    description: str
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    why_suggested: Optional[str] = None
    confidence: Optional[float] = None
    planning_style: Optional[str] = "baseline"


class ModelRating(BaseModel):
    ratings: Dict[str, float] = Field(default_factory=dict)
    reasoning: str = ""


class VariantMetadata(BaseModel):
    step_count: Optional[int] = None
    complexity_score: Optional[str] = None
    optimization_notes: Optional[str] = None
    estimated_time_minutes: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class VariantData(BaseModel):
    execution_graph: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: VariantMetadata = Field(default_factory=VariantMetadata)


class ExecutionStepsList(BaseModel):
    steps: List["ExecutionStep"] = Field(default_factory=list)


class StrawmanProposalInputList(BaseModel):
    proposals: List[StrawmanProposalInput] = Field(default_factory=list)
