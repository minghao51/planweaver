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


class StrawmanProposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    selected: bool = False


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
    external_contexts: List[ExternalContext] = Field(default_factory=list, description="External context sources for enhanced planning")
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
    proposal_ids: List[str]
