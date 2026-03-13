from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, Query, Depends, Request

from ...models.plan import PlanStatus, ComparisonRequest, ProposalComparison
from ...services.comparison_service import ProposalComparisonService
from ..dependencies import get_orchestrator, get_plan_or_404, get_comparison_service
from ..schemas import (
    AnswerQuestionsRequest,
    BranchCandidateRequest,
    CandidateListResponse,
    CandidateOperationResponse,
    CandidateOutcomesResponse,
    CreateSessionRequest,
    ExecutePlanRequest,
    RefineCandidateRequest,
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
        plan = orch.start_session(
            body.user_intent,
            body.scenario_name,
            planner_model=body.planner_model,
            executor_model=body.executor_model,
        )
        return serialize_plan_summary(plan)
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=400, detail=f"Cannot complete operation: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error creating session")
        raise HTTPException(
            status_code=500, detail="Operation failed. Please try again."
        )


@router.get("/sessions")
@limiter.limit("60/minute")
def list_sessions(
    request: Request,
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
    except Exception:
        logger.exception("Unexpected error getting session")
        raise HTTPException(
            status_code=500, detail="Operation failed. Please try again."
        )


@router.post("/sessions/{session_id}/questions")
@limiter.limit("30/minute")
def answer_questions(
    request: Request, session_id: str, answers: AnswerQuestionsRequest
):
    orch, plan = get_plan_or_404(session_id)
    updated_plan = orch.answer_questions(plan, answers.answers)
    return {
        "status": updated_plan.status.value,
        "open_questions": [q.model_dump() for q in updated_plan.open_questions],
        "execution_graph": serialize_execution_graph(updated_plan),
        "candidate_plans": [
            c.model_dump(mode="json") for c in updated_plan.candidate_plans
        ],
        "context_suggestions": [
            s.model_dump(mode="json") for s in updated_plan.context_suggestions
        ],
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
        "selected_candidate_id": updated_plan.selected_candidate_id,
        "candidate_plans": [
            c.model_dump(mode="json") for c in updated_plan.candidate_plans
        ],
    }


@router.post("/sessions/{session_id}/approve")
def approve_plan(session_id: str):
    try:
        orch, plan = get_plan_or_404(session_id)
        if not plan.execution_graph:
            raise HTTPException(
                status_code=400,
                detail="No execution steps to approve. Please select a proposal first.",
            )

        updated_plan = orch.approve_plan(plan)
        return {
            "status": updated_plan.status.value,
            "execution_graph": serialize_execution_graph(updated_plan),
            "approved_candidate_id": updated_plan.approved_candidate_id,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error approving plan")
        raise HTTPException(
            status_code=500, detail="Operation failed. Please try again."
        )


@router.post("/sessions/{session_id}/execute")
@limiter.limit("10/hour")
async def execute_plan(
    request: Request, session_id: str, body: Optional[ExecutePlanRequest] = None
):
    try:
        orch, plan = get_plan_or_404(session_id)
        if plan.status != PlanStatus.APPROVED:
            raise HTTPException(
                status_code=400, detail="Plan must be approved before execution"
            )

        result = await orch.execute(plan, body.context if body else {})
        return {
            "status": result.status.value,
            "final_output": result.final_output,
            "execution_graph": serialize_execution_graph(result),
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error executing plan")
        raise HTTPException(
            status_code=500, detail="Operation failed. Please try again."
        )


@router.post(
    "/sessions/{session_id}/compare-proposals", response_model=ProposalComparison
)
@limiter.limit("10/hour")
def compare_proposals(
    http_request: Request,
    session_id: str,
    request: ComparisonRequest,
    comparison_service: ProposalComparisonService = Depends(get_comparison_service),
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
            status_code=404, detail=f"Proposals not found: {sorted(invalid_ids)}"
        )

    if len(request.proposal_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Comparison requires at least 2 proposals. Got {len(request.proposal_ids)}",
        )

    if len(request.proposal_ids) > 10:
        raise HTTPException(
            status_code=400,
            detail=f"Comparison supports a maximum of 10 proposals. Got {len(request.proposal_ids)}",
        )

    try:
        comparison = comparison_service.compare_proposals(
            plan=plan, proposal_ids=request.proposal_ids
        )
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(
            status_code=500, detail="Unable to generate comparison. Please try again."
        )


@router.get(
    "/sessions/{session_id}/candidates",
    response_model=CandidateListResponse,
)
@limiter.limit("60/minute")
def list_candidates(request: Request, session_id: str):
    orch, plan = get_plan_or_404(session_id)
    candidates = orch.list_candidates(plan)
    return {
        "session_id": session_id,
        "selected_candidate_id": plan.selected_candidate_id,
        "approved_candidate_id": plan.approved_candidate_id,
        "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
    }


@router.post(
    "/sessions/{session_id}/candidates/{candidate_id}/refine",
    response_model=CandidateOperationResponse,
)
@limiter.limit("30/minute")
def refine_candidate(
    request: Request,
    session_id: str,
    candidate_id: str,
    body: RefineCandidateRequest,
):
    orch, plan = get_plan_or_404(session_id)
    try:
        candidate = orch.refine_candidate(
            plan,
            candidate_id,
            body.operation,
            step_id=body.step_id,
            task=body.task,
            insert_after_step_id=body.insert_after_step_id,
            note=body.note,
        )
        refreshed = orch.get_session(session_id)
        assert refreshed is not None
        return {
            "session_id": session_id,
            "selected_candidate_id": refreshed.selected_candidate_id,
            "approved_candidate_id": refreshed.approved_candidate_id,
            "candidate": candidate.model_dump(mode="json"),
            "execution_graph": serialize_execution_graph(refreshed),
            "status": refreshed.status.value,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/candidates/{candidate_id}/branch",
    response_model=CandidateOperationResponse,
)
@limiter.limit("30/minute")
def branch_candidate(
    request: Request,
    session_id: str,
    candidate_id: str,
    body: BranchCandidateRequest,
):
    orch, plan = get_plan_or_404(session_id)
    try:
        candidate = orch.branch_candidate(
            plan, candidate_id, title=body.title, note=body.note
        )
        refreshed = orch.get_session(session_id)
        assert refreshed is not None
        return {
            "session_id": session_id,
            "selected_candidate_id": refreshed.selected_candidate_id,
            "approved_candidate_id": refreshed.approved_candidate_id,
            "candidate": candidate.model_dump(mode="json"),
            "execution_graph": serialize_execution_graph(refreshed),
            "status": refreshed.status.value,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/candidates/{candidate_id}/approve",
    response_model=CandidateOperationResponse,
)
@limiter.limit("30/minute")
def approve_candidate(request: Request, session_id: str, candidate_id: str):
    orch, plan = get_plan_or_404(session_id)
    try:
        updated_plan = orch.approve_candidate(plan, candidate_id)
        candidate = updated_plan.get_candidate_by_id(candidate_id)
        return {
            "session_id": session_id,
            "selected_candidate_id": updated_plan.selected_candidate_id,
            "approved_candidate_id": updated_plan.approved_candidate_id,
            "candidate": candidate.model_dump(mode="json"),
            "execution_graph": serialize_execution_graph(updated_plan),
            "status": updated_plan.status.value,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/sessions/{session_id}/outcomes",
    response_model=CandidateOutcomesResponse,
)
@limiter.limit("60/minute")
def list_outcomes(request: Request, session_id: str):
    orch, plan = get_plan_or_404(session_id)
    return {
        "session_id": session_id,
        "outcomes": [
            outcome.model_dump(mode="json") for outcome in orch.get_outcomes(plan)
        ],
    }
