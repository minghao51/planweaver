from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from datetime import datetime, timezone
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
