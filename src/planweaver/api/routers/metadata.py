from fastapi import APIRouter

from ..dependencies import get_orchestrator

router = APIRouter()


@router.get("/scenarios")
def list_scenarios():
    orch = get_orchestrator()
    return {"scenarios": orch.template_engine.list_scenarios()}


@router.get("/models")
def list_models():
    orch = get_orchestrator()
    return {"models": orch.llm.get_available_models()}
