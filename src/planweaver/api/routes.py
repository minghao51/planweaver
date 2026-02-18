from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from typing import Dict, Any, Optional
from functools import lru_cache
from pydantic import BaseModel, Field, field_validator
import re

from ..orchestrator import Orchestrator
from ..models.plan import PlanStatus
from ..services.context_service import ContextService
from ..config import Settings

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


def get_context_service() -> ContextService:
    orch = get_orchestrator()
    return ContextService(orch.planner.llm.settings if hasattr(orch.planner.llm, 'settings') else Settings(), orch.planner.llm)


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


# Context management endpoints
class GitHubContextRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")


class WebSearchContextRequest(BaseModel):
    query: Optional[str] = Field(None, description="Search query (optional, auto-generated from intent if not provided)")


@router.post("/sessions/{session_id}/context/github")
async def add_github_context(
    session_id: str,
    request: GitHubContextRequest
):
    """Add GitHub repository context to planning session"""
    orch = get_orchestrator()
    context_service = get_context_service()

    plan = orch.get_session(session_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Process GitHub context
        context = await context_service.add_github_context(request.repo_url)

        # Add to plan
        plan = orch.add_external_context(session_id, context)

        return {
            "context_id": context.id,
            "source_type": context.source_type,
            "status": "added"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add GitHub context: {str(e)}")


@router.post("/sessions/{session_id}/context/web-search")
async def add_web_search_context(
    session_id: str,
    request: WebSearchContextRequest
):
    """Add web search results to planning session.
    If query not provided, generates one from session intent."""
    orch = get_orchestrator()
    context_service = get_context_service()

    plan = orch.get_session(session_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Get plan to generate query if needed
        query = request.query
        if not query:
            query = f"best practices for: {plan.user_intent}"

        # Process web search
        context = await context_service.add_web_search_context(query)

        # Add to plan
        plan = orch.add_external_context(session_id, context)

        return {
            "context_id": context.id,
            "source_type": context.source_type,
            "query": query,
            "status": "added"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add web search: {str(e)}")


@router.post("/sessions/{session_id}/context/upload")
async def upload_file_context(
    session_id: str,
    file: UploadFile = File(..., description="File to upload for context")
):
    """Upload file and extract context for planning"""
    orch = get_orchestrator()
    context_service = get_context_service()

    plan = orch.get_session(session_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Read file content
        content = await file.read()

        # Process file
        context = await context_service.add_file_context(file.filename, content)

        # Add to plan
        plan = orch.add_external_context(session_id, context)

        return {
            "context_id": context.id,
            "source_type": context.source_type,
            "filename": file.filename,
            "status": "added"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@router.get("/sessions/{session_id}/context")
def list_contexts(session_id: str):
    """List all external contexts for a session"""
    orch = get_orchestrator()
    plan = orch.get_session(session_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "contexts": [
            {
                "id": ctx.id,
                "source_type": ctx.source_type,
                "source_url": ctx.source_url,
                "created_at": ctx.created_at,
                "metadata": {k: v for k, v in ctx.metadata.items() if k != "full_content"}
            }
            for ctx in plan.external_contexts
        ]
    }
