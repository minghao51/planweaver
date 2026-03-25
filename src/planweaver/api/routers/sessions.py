from typing import Optional, cast, Literal
import logging
import inspect

from fastapi import APIRouter, HTTPException, Query, Depends, Request

from ...models.plan import Plan, PlanStatus, ComparisonRequest, ProposalComparison
from ...models.session import SessionState, SessionMessage, NegotiatorIntent
from ...services.comparison_service import ProposalComparisonService
from ...session import SessionStateMachine
from ...negotiator import Negotiator
from ..dependencies import get_orchestrator, get_plan_or_404, get_comparison_service
from ..schemas import (
    AnswerQuestionsRequest,
    BranchCandidateRequest,
    CandidateListResponse,
    CandidateOperationResponse,
    CandidateOutcomesResponse,
    CreateSessionRequest,
    ExecutePlanRequest,
    MessageRequest,
    MessageResponse,
    RefineCandidateRequest,
)
from ..serializers import (
    serialize_execution_graph,
    serialize_plan_detail,
    serialize_session_history_item,
    serialize_plan_summary,
)
from ..middleware import limiter
from ...db.database import SessionLocal
from ...db.models import SessionMessageModel

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sessions")
@limiter.limit("10/hour")
async def create_session(request: Request, body: CreateSessionRequest):
    try:
        orch = get_orchestrator()

        # Route to appropriate planning mode
        if body.planning_mode == "specialist":
            plan = await orch.start_specialist_session(
                body.user_intent,
                body.scenario_name,
                body.specialist_domains,
                body.planner_model,
                body.executor_model,
            )
        elif body.planning_mode == "ensemble":
            plan = await orch.start_ensemble_session(
                body.user_intent,
                body.scenario_name,
                body.ensemble_models,
                body.planner_model,
                body.executor_model,
            )
        elif body.planning_mode == "debate":
            plan = await orch.start_debate_session(
                body.user_intent,
                body.scenario_name,
                body.planner_model,
                body.executor_model,
            )
        else:
            # Baseline mode (existing flow)
            plan = None
            start_session_async = getattr(orch, "start_session_async", None)
            if callable(start_session_async):
                result = start_session_async(
                    body.user_intent,
                    body.scenario_name,
                    external_contexts=None,
                    planner_model=body.planner_model,
                    executor_model=body.executor_model,
                )
                if inspect.isawaitable(result):
                    plan = await result
                else:
                    plan = result
            if plan is None:
                plan = orch.start_session(
                    body.user_intent,
                    body.scenario_name,
                    planner_model=body.planner_model,
                    executor_model=body.executor_model,
                )

        assert plan is not None, "Plan should never be None at this point"
        return serialize_plan_summary(plan)
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Cannot complete operation: {str(e)}")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error creating session")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


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
        orch = get_orchestrator()
        plan = orch.get_session(session_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Session not found")
        return serialize_plan_detail(plan)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error getting session")
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
        "candidate_plans": [c.model_dump(mode="json") for c in updated_plan.candidate_plans],
        "context_suggestions": [s.model_dump(mode="json") for s in updated_plan.context_suggestions],
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
        "candidate_plans": [c.model_dump(mode="json") for c in updated_plan.candidate_plans],
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error approving plan")
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
    except Exception:
        logger.exception("Unexpected error executing plan")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


@router.post("/sessions/{session_id}/compare-proposals", response_model=ProposalComparison)
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
        raise HTTPException(status_code=404, detail=f"Proposals not found: {sorted(invalid_ids)}")

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
        comparison = comparison_service.compare_proposals(plan=plan, proposal_ids=request.proposal_ids)
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to generate comparison. Please try again.")


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
        candidate = orch.branch_candidate(plan, candidate_id, title=body.title, note=body.note)
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
        "outcomes": [outcome.model_dump(mode="json") for outcome in orch.get_outcomes(plan)],
    }


@router.get("/sessions/{session_id}/similar-plans")
@limiter.limit("30/minute")
async def get_similar_plans(
    request: Request,
    session_id: str,
    query: str = Query(default="", description="Search query for similar plans"),
    limit: int = Query(default=5, ge=1, le=20),
):
    """Get similar historical plans using memory layer search."""
    try:
        orch, plan = get_plan_or_404(session_id)

        # Use user_intent as default query if not provided
        search_query = query or plan.user_intent

        results = await orch.search_similar_plans(
            query=search_query,
            limit=limit,
            similarity_threshold=0.7,
        )

        return {
            "session_id": session_id,
            "query": search_query,
            "similar_plans": results,
            "count": len(results),
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error getting similar plans")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


def _get_message_history(session_id: str) -> list:
    """Get message history for a session."""
    db = SessionLocal()
    try:
        messages = (
            db.query(SessionMessageModel)
            .filter(SessionMessageModel.session_id == session_id)
            .order_by(SessionMessageModel.created_at.asc())
            .all()
        )
        return [m.to_dict() for m in messages]
    finally:
        db.close()


def _save_session_message(message: SessionMessage) -> None:
    """Save a session message to the database."""
    db = SessionLocal()
    try:
        db_message = SessionMessageModel(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            intent=message.intent.value if message.intent else None,
            extra_data=message.metadata,
        )
        db.add(db_message)
        db.commit()
    finally:
        db.close()


def _intent_to_event(intent: NegotiatorIntent) -> str:
    """Map negotiator intent to state machine event."""
    mapping = {
        NegotiatorIntent.APPROVE: "approve",
        NegotiatorIntent.REJECT: "cancel",
        NegotiatorIntent.EXECUTE: "approve",
        NegotiatorIntent.ANSWER: "all_questions_answered",
        NegotiatorIntent.REVISE: "request_revision",
    }
    return mapping.get(intent, "request_revision")


def _plan_status_to_session_state(plan: Plan) -> SessionState:
    """Map persisted plan state into the conversational session state machine."""
    if plan.status == PlanStatus.EXECUTING:
        return SessionState.EXECUTING
    if plan.status in {PlanStatus.COMPLETED, PlanStatus.FAILED}:
        return SessionState.DONE
    if plan.status in {PlanStatus.AWAITING_APPROVAL, PlanStatus.APPROVED}:
        return SessionState.NEGOTIATING
    if any(not question.answered for question in plan.open_questions):
        return SessionState.CLARIFYING
    return SessionState.PLANNING


def _session_transition_event(
    current_state: SessionState,
    next_state: SessionState,
    intent: NegotiatorIntent,
) -> Optional[str]:
    """Resolve a valid state machine event for an LLM-requested transition."""
    direct_mapping = {
        (SessionState.GOAL_RECEIVED, SessionState.CLARIFYING): "start_clarifying",
        (SessionState.GOAL_RECEIVED, SessionState.PLANNING): "start_planning",
        (SessionState.CLARIFYING, SessionState.PLANNING): "all_questions_answered",
        (SessionState.PLANNING, SessionState.NEGOTIATING): "plan_ready",
        (SessionState.NEGOTIATING, SessionState.PLANNING): "request_revision",
        (SessionState.NEGOTIATING, SessionState.EXECUTING): "approve",
        (SessionState.EXECUTING, SessionState.DONE): "execution_complete",
    }
    if current_state == next_state:
        return None
    direct_event = direct_mapping.get((current_state, next_state))
    if direct_event is not None:
        return direct_event
    if next_state == SessionState.DONE:
        return "cancel"
    return _intent_to_event(intent)


def _session_state_to_plan_status(current_status: PlanStatus, next_state: SessionState) -> PlanStatus:
    """Map conversational session transitions back into persisted plan state."""
    if next_state in {SessionState.GOAL_RECEIVED, SessionState.CLARIFYING, SessionState.PLANNING}:
        return PlanStatus.BRAINSTORMING
    if next_state == SessionState.NEGOTIATING:
        return PlanStatus.AWAITING_APPROVAL
    if next_state == SessionState.EXECUTING:
        # Approval happens here, but actual execution still runs through /execute.
        return PlanStatus.APPROVED
    return current_status


def _restore_convergence_state(state_machine: SessionStateMachine, plan: Plan) -> None:
    counters = plan.metadata.get("negotiation_convergence")
    if not isinstance(counters, dict):
        return
    rounds_without_change = counters.get("rounds_without_change", 0)
    last_mutation_round = counters.get("last_mutation_round", 0)
    if isinstance(rounds_without_change, int) and isinstance(last_mutation_round, int):
        state_machine.load_convergence_state(rounds_without_change, last_mutation_round)


def _persist_convergence_state(state_machine: SessionStateMachine, plan: Plan) -> None:
    if state_machine.get_state() == SessionState.NEGOTIATING:
        plan.metadata["negotiation_convergence"] = state_machine.dump_convergence_state()
    else:
        plan.metadata.pop("negotiation_convergence", None)


@router.post("/sessions/{session_id}/message", response_model=MessageResponse)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    session_id: str,
    body: MessageRequest,
):
    """
    Universal endpoint for all session communication.

    This endpoint replaces the fragmented approve/reject/questions endpoints
    with a single unified interface. The Negotiator classifies intent and
    applies appropriate mutations to the plan.
    """
    orch, plan = get_plan_or_404(session_id)

    current_state = _plan_status_to_session_state(plan)
    state_machine = SessionStateMachine(session_id, current_state)
    _restore_convergence_state(state_machine, plan)

    negotiator = Negotiator()

    message_history = _get_message_history(session_id)

    output = await negotiator.process(
        message=body.content,
        plan=plan,
        session_state=state_machine.get_state(),
        message_history=message_history,
    )

    had_mutation = len(output.mutations) > 0

    if output.mutations:
        plan = negotiator.apply_mutations(output.mutations, plan)

    if output.state_transition:
        transition_event = _session_transition_event(state_machine.get_state(), output.state_transition, output.intent)
        if transition_event:
            state_machine.transition(transition_event, {"mutations": len(output.mutations)})
        plan.status = _session_state_to_plan_status(plan.status, output.state_transition)
    else:
        state_machine.record_negotiation_round(had_mutation)

    session_message = SessionMessage(
        session_id=session_id,
        role=cast(Literal["user", "assistant", "system"], body.role),
        content=body.content,
        intent=output.intent,
        metadata=body.metadata,
    )
    _save_session_message(session_message)
    _save_session_message(
        SessionMessage(
            session_id=session_id,
            role="assistant",
            content=output.response_message,
            intent=output.intent,
            metadata={
                "state_transition": output.state_transition.value if output.state_transition else None,
                "mutations_applied": len(output.mutations),
            },
        )
    )

    _persist_convergence_state(state_machine, plan)
    orch.plan_repository.save(plan)

    convergence = None
    if state_machine.get_state() == SessionState.NEGOTIATING:
        convergence = state_machine.check_convergence()

    return MessageResponse(
        session_id=session_id,
        state=state_machine.get_state().value,
        response_message=output.response_message,
        intent=output.intent.value,
        mutations_applied=len(output.mutations),
        state_transition=output.state_transition.value if output.state_transition else None,
        convergence_status=convergence.model_dump() if convergence else None,
        session=serialize_plan_detail(plan),
    )
