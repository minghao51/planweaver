from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, Query, Depends, Request

from ...models.plan import PlanStatus, ComparisonRequest, ProposalComparison
from ...services.comparison_service import ProposalComparisonService
from ..dependencies import get_orchestrator, get_plan_or_404, get_comparison_service
from ..schemas import (
    AnswerQuestionsRequest,
    CreateSessionRequest,
    ExecutePlanRequest,
)
from ..serializers import (
    serialize_execution_graph,
    serialize_plan_detail,
    serialize_session_history_item,
    serialize_plan_summary,
)
from ..middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sessions")
@limiter.limit("10/hour")
def create_session(request: Request, body: CreateSessionRequest):
    try:
        orch = get_orchestrator()
        plan = orch.start_session(body.user_intent, body.scenario_name)
        return serialize_plan_summary(plan)
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Cannot complete operation: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error creating session")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


@router.get("/sessions")
@limiter.limit("60/minute")
def list_sessions(request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
):
    orch = get_orchestrator()
    result = orch.list_sessions(limit=limit, offset=offset, status=status, query=q)
    return {
        "sessions": [serialize_session_history_item(s) for s in result["sessions"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    }


@router.get("/sessions/{session_id}")
@limiter.limit("60/minute")
def get_session(request: Request, session_id: str):
    try:
        _, plan = get_plan_or_404(session_id)
        return serialize_plan_detail(plan)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error getting session")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


@router.post("/sessions/{session_id}/questions")
@limiter.limit("30/minute")
def answer_questions(request: Request, session_id: str, answers: AnswerQuestionsRequest):
    orch, plan = get_plan_or_404(session_id)
    updated_plan = orch.answer_questions(plan, answers.answers)
    return {
        "status": updated_plan.status.value,
        "open_questions": [q.model_dump() for q in updated_plan.open_questions],
        "execution_graph": serialize_execution_graph(updated_plan),
    }


@router.get("/sessions/{session_id}/proposals")
def get_proposals(session_id: str):
    orch, plan = get_plan_or_404(session_id)
    return {"proposals": orch.get_strawman_proposals(plan)}


@router.post("/sessions/{session_id}/proposals/{proposal_id}/select")
def select_proposal(session_id: str, proposal_id: str):
    orch, plan = get_plan_or_404(session_id)
    updated_plan = orch.select_proposal(plan, proposal_id)
    return {
        "status": updated_plan.status.value,
        "locked_constraints": updated_plan.locked_constraints,
    }


@router.post("/sessions/{session_id}/approve")
def approve_plan(session_id: str):
    try:
        orch, plan = get_plan_or_404(session_id)
        if not plan.execution_graph:
            raise HTTPException(status_code=400, detail="No execution steps to approve. Please select a proposal first.")

        updated_plan = orch.approve_plan(plan)
        return {
            "status": updated_plan.status.value,
            "execution_graph": serialize_execution_graph(updated_plan),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error approving plan")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


@router.post("/sessions/{session_id}/execute")
@limiter.limit("10/hour")
async def execute_plan(request: Request, session_id: str, body: Optional[ExecutePlanRequest] = None):
    try:
        orch, plan = get_plan_or_404(session_id)
        if plan.status != PlanStatus.APPROVED:
            raise HTTPException(status_code=400, detail="Plan must be approved before execution")

        result = await orch.execute(plan, body.context if body else {})
        return {
            "status": result.status.value,
            "final_output": result.final_output,
            "execution_graph": serialize_execution_graph(result),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error executing plan")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


@router.post("/sessions/{session_id}/compare-proposals", response_model=ProposalComparison)
@limiter.limit("10/hour")
def compare_proposals(
    http_request: Request,
    session_id: str,
    request: ComparisonRequest,
    comparison_service: ProposalComparisonService = Depends(get_comparison_service)
):
    """Compare detailed execution graphs for selected proposals.

    Args:
        session_id: Session identifier
        request: Comparison request with proposal_ids to compare

    Returns:
        ProposalComparison with full execution graphs and diff analysis

    Raises:
        HTTPException 404: If proposal IDs are invalid
        HTTPException 400: If fewer than 2 or more than 10 proposals provided
    """
    _, plan = get_plan_or_404(session_id)

    # Validate proposal IDs
    valid_ids = {p.id for p in plan.strawman_proposals}
    invalid_ids = set(request.proposal_ids) - valid_ids

    if invalid_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Proposals not found: {sorted(invalid_ids)}"
        )

    if len(request.proposal_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Comparison requires at least 2 proposals. Got {len(request.proposal_ids)}"
        )

    if len(request.proposal_ids) > 10:
        raise HTTPException(
            status_code=400,
            detail=f"Comparison supports a maximum of 10 proposals. Got {len(request.proposal_ids)}"
        )

    try:
        comparison = comparison_service.compare_proposals(
            plan=plan,
            proposal_ids=request.proposal_ids
        )
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate comparison. Please try again."
        )
