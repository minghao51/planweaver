from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
from datetime import datetime, timezone
import uuid


class SessionState(str, Enum):
    GOAL_RECEIVED = "goal_received"
    CLARIFYING = "clarifying"
    PLANNING = "planning"
    NEGOTIATING = "negotiating"
    EXECUTING = "executing"
    DONE = "done"


class NegotiatorIntent(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"
    ASK_QUESTION = "ask_question"
    ANSWER = "answer"
    EXECUTE = "execute"
    CANCEL = "cancel"
    PROVIDE_CONTEXT = "provide_context"
    STATUS_QUERY = "status_query"


class PlanMutationType(str, Enum):
    LOCK_CONSTRAINT = "lock_constraint"
    UNLOCK_CONSTRAINT = "unlock_constraint"
    ADD_QUESTION = "add_question"
    ANSWER_QUESTION = "answer_question"
    SELECT_CANDIDATE = "select_candidate"
    APPROVE_CANDIDATE = "approve_candidate"
    EDIT_STEP = "edit_step"
    ADD_STEP = "add_step"
    DELETE_STEP = "delete_step"
    REGENERATE_STEPS = "regenerate_steps"
    ADD_CONTEXT = "add_context"
    BRANCH_CANDIDATE = "branch_candidate"


class PlanMutation(BaseModel):
    mutation_type: PlanMutationType
    step_id: Optional[int] = None
    key: Optional[str] = None
    value: Any = None
    description: Optional[str] = None


class NegotiatorOutput(BaseModel):
    intent: NegotiatorIntent
    response_message: str
    mutations: List[PlanMutation] = Field(default_factory=list)
    state_transition: Optional[SessionState] = None
    clarification_questions: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class SessionMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    intent: Optional[NegotiatorIntent] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StateTransitionEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    from_state: Optional[SessionState]
    to_state: SessionState
    event: str
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConvergenceStatus(BaseModel):
    is_converged: bool
    rounds_without_change: int
    last_mutation_round: int
    reasons: List[str] = Field(default_factory=list)
