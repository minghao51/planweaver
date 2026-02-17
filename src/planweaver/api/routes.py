from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from functools import lru_cache
from pydantic import BaseModel, Field, field_validator
import re

from ..orchestrator import Orchestrator
from ..models.plan import PlanStatus

router = APIRouter()


class CreateSessionRequest(BaseModel):
    user_intent: str = Field(..., min_length=1, max_length=10000)
    scenario_name: Optional[str] = Field(None, max_length=200)

    @field_validator('user_intent', mode='before')
    @classmethod
    def sanitize_input(cls, v):
        if isinstance(v, str):
            return cls._sanitize(v)
        return v

    @staticmethod
    def _sanitize(text: str) -> str:
        text = text.strip()
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return text


class AnswerQuestionsRequest(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict)

    @field_validator('answers', mode='before')
    @classmethod
    def sanitize_answers(cls, v):
        if isinstance(v, dict):
            return {k: CreateSessionRequest._sanitize(str(v)) for k, v in v.items()}
        return {}


class ExecutePlanRequest(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)


@lru_cache
def get_orchestrator_factory() -> Orchestrator:
    return Orchestrator()


def get_orchestrator() -> Orchestrator:
    return get_orchestrator_factory()


@router.post("/sessions")
def create_session(request: CreateSessionRequest):
    orch = get_orchestrator()
    plan = orch.start_session(request.user_intent, request.scenario_name)
    return {
        "session_id": plan.session_id,
        "status": plan.status.value,
        "open_questions": [q.model_dump() for q in plan.open_questions]
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    orch = get_orchestrator()
    plan = orch.get_session(session_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": plan.session_id,
        "status": plan.status.value,
        "user_intent": plan.user_intent,
        "locked_constraints": plan.locked_constraints,
        "open_questions": [q.model_dump() for q in plan.open_questions],
        "strawman_proposals": [p.model_dump() for p in plan.strawman_proposals],
        "execution_graph": [s.model_dump() for s in plan.execution_graph]
    }


@router.post("/sessions/{session_id}/questions")
def answer_questions(session_id: str, answers: AnswerQuestionsRequest):
    orch = get_orchestrator()
    plan = orch.get_session(session_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    updated_plan = orch.answer_questions(plan, answers.answers)
    return {
        "status": updated_plan.status.value,
        "open_questions": [q.model_dump() for q in updated_plan.open_questions],
        "execution_graph": [s.model_dump() for s in updated_plan.execution_graph]
    }


@router.get("/sessions/{session_id}/proposals")
def get_proposals(session_id: str):
    orch = get_orchestrator()
    plan = orch.get_session(session_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    proposals = orch.get_strawman_proposals(plan)
    return {"proposals": proposals}


@router.post("/sessions/{session_id}/proposals/{proposal_id}/select")
def select_proposal(session_id: str, proposal_id: str):
    orch = get_orchestrator()
    plan = orch.get_session(session_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    updated_plan = orch.select_proposal(plan, proposal_id)
    return {"status": updated_plan.status.value, "locked_constraints": updated_plan.locked_constraints}


@router.post("/sessions/{session_id}/approve")
def approve_plan(session_id: str):
    orch = get_orchestrator()
    plan = orch.get_session(session_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    if not plan.execution_graph:
        raise HTTPException(status_code=400, detail="No execution steps to approve")

    updated_plan = orch.approve_plan(plan)
    return {
        "status": updated_plan.status.value,
        "execution_graph": [s.model_dump() for s in updated_plan.execution_graph]
    }


@router.post("/sessions/{session_id}/execute")
def execute_plan(session_id: str, request: Optional[ExecutePlanRequest] = None):
    orch = get_orchestrator()
    plan = orch.get_session(session_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    if plan.status != PlanStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Plan must be approved before execution")

    result = orch.execute(plan, request.context if request else {})
    return {
        "status": result.status.value,
        "final_output": result.final_output,
        "execution_graph": [s.model_dump() for s in result.execution_graph]
    }


@router.get("/scenarios")
def list_scenarios():
    orch = get_orchestrator()
    return {"scenarios": orch.template_engine.list_scenarios()}


@router.get("/models")
def list_models():
    orch = get_orchestrator()
    return {"models": orch.llm.get_available_models()}
