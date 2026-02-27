from fastapi import APIRouter, Request

from ..dependencies import get_orchestrator
from ..middleware import limiter

router = APIRouter()


@router.get("/scenarios")
@limiter.limit("30/minute")
def list_scenarios(request: Request):
    orch = get_orchestrator()
    return {"scenarios": orch.template_engine.list_scenarios()}


@router.get("/models")
@limiter.limit("30/minute")
def list_models(request: Request):
    orch = get_orchestrator()
    return {"models": orch.llm.get_available_models()}
