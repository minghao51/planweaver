from typing import TYPE_CHECKING

from fastapi import HTTPException

from ..config import get_settings
from ..orchestrator import Orchestrator
from ..services.comparison_service import ProposalComparisonService
from ..services.context_service import ContextService

if TYPE_CHECKING:
    from ..models.plan import Plan

_orchestrator: Orchestrator | None = None


def _get_orchestrator_instance() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def get_orchestrator() -> Orchestrator:
    return _get_orchestrator_instance()


def reset_orchestrator() -> None:
    global _orchestrator
    _orchestrator = None


def get_context_service() -> ContextService:
    orch = get_orchestrator()
    settings = getattr(orch.llm, "settings", get_settings())
    return ContextService(settings, orch.llm)


def get_comparison_service() -> ProposalComparisonService:
    orch = get_orchestrator()
    return ProposalComparisonService(orch.planner, orch.llm)


def plan_or_404(session_id: str) -> tuple[Orchestrator, "Plan"]:
    orch = get_orchestrator()
    plan = orch.get_session(session_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")
    return orch, plan
