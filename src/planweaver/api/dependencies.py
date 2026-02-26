from functools import lru_cache

from fastapi import HTTPException

from ..config import get_settings
from ..orchestrator import Orchestrator
from ..services.context_service import ContextService
from ..services.comparison_service import ProposalComparisonService


@lru_cache
def get_orchestrator_factory() -> Orchestrator:
    return Orchestrator()


def get_orchestrator() -> Orchestrator:
    return get_orchestrator_factory()


def get_context_service() -> ContextService:
    orch = get_orchestrator()
    settings = getattr(orch.llm, "settings", get_settings())
    return ContextService(settings, orch.llm)


def get_comparison_service() -> ProposalComparisonService:
    orch = get_orchestrator()
    return ProposalComparisonService(orch.planner, orch.llm)


def get_plan_or_404(session_id: str):
    orch = get_orchestrator()
    try:
        plan = orch.get_session(session_id)
    except ValueError:
        plan = None

    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")

    return orch, plan
