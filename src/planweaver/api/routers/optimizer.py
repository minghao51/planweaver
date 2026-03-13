import logging
import uuid

from fastapi import APIRouter, HTTPException, Request

from ...db.database import get_session
from ...services.optimizer_service import OptimizerService
from ..dependencies import get_orchestrator
from ..schemas import (
    ManualPlanRequest,
    ManualPlanResponse,
    NormalizePlanRequest,
    NormalizePlanResponse,
    PairwiseComparisonRequest,
    PairwiseComparisonResponse,
    PlanRatingsSchema,
    PlanEvaluationRequest,
    PlanEvaluationResponse,
    OptimizerRequest,
    OptimizerResponse,
    RatePlansRequest,
    RatePlansResponse,
    UserRatingRequest,
    UserRatingResponse,
    OptimizationStateResponse,
)
from ..middleware import limiter
from ...db.models import UserRating
from ...models.plan import ManualPlanSubmission, NormalizedStep, PlanSourceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimizer", tags=["optimizer"])


def get_optimizer_service():
    """Get OptimizerService instance"""
    db = get_session()
    try:
        return OptimizerService(db)
    finally:
        pass  # Keep session open for service to use


def _normalize_source_type(source_type: str) -> PlanSourceType:
    try:
        return PlanSourceType(source_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source_type '{source_type}'.",
        ) from exc


@router.post("/optimize", response_model=OptimizerResponse)
@limiter.limit("10/hour")
def optimize_plan(request: Request, body: OptimizerRequest):
    """
    Generate optimized variants of a selected proposal and rate all plans.

    This endpoint:
    1. Generates optimized variants (simplified, enhanced, cost-optimized)
    2. Rates the original proposal and all variants using multiple AI models
    3. Returns optimization results for comparison
    """
    try:
        optimizer = get_optimizer_service()

        candidate_id = body.candidate_id or body.selected_proposal_id
        if not candidate_id:
            raise HTTPException(
                status_code=400,
                detail="candidate_id is required when no selected_proposal_id is supplied.",
            )
        session_id = body.session_id or candidate_id[:36]

        results = optimizer.optimize_plan(
            session_id=session_id,
            selected_candidate_id=candidate_id,
            optimization_types=body.optimization_types,
            rate_with_models=["claude-3.5-sonnet", "gpt-4o", "deepseek-chat"],
        )

        return OptimizerResponse(
            optimization_id=str(uuid.uuid4()),
            status=results.get("status", "unknown"),
            variants=results.get("variants", []),
            ratings=results.get("ratings", {}),
            session_id=session_id,
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=400, detail=f"Cannot complete operation: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error optimizing plan")
        raise HTTPException(
            status_code=500, detail="Operation failed. Please try again."
        )


@router.get("/results/{session_id}")
@limiter.limit("60/minute")
def get_optimization_results(request: Request, session_id: str):
    """
    Get optimization results for a session.

    Returns all variants and ratings for the specified session.
    """
    try:
        optimizer = get_optimizer_service()
        results = optimizer.get_optimization_results(session_id)
        return results

    except Exception:
        logger.exception("Unexpected error getting optimization results")
        raise HTTPException(
            status_code=500, detail="Operation failed. Please try again."
        )


@router.post("/rate", response_model=RatePlansResponse)
@limiter.limit("30/hour")
def rate_plans(request: Request, body: RatePlansRequest):
    """
    Rate plans using multiple AI models.

    This endpoint rates the specified plans using multiple AI models
    for comparison on various criteria.
    """
    try:
        ratings_by_plan: dict[str, PlanRatingsSchema] = {}

        for plan_id in body.plan_ids:
            # For now, we need plan data
            # In production, you'd fetch from database
            logger.warning(f"Rating plan {plan_id} - needs plan data from database")
            ratings_by_plan[plan_id] = PlanRatingsSchema(
                plan_id=plan_id,
                ratings={},
                average_score=5.0,
            )

        return RatePlansResponse(
            rating_id=str(uuid.uuid4()), status="completed", ratings=ratings_by_plan
        )

    except Exception:
        logger.exception("Unexpected error rating plans")
        raise HTTPException(
            status_code=500, detail="Operation failed. Please try again."
        )


@router.post("/user-rating", response_model=UserRatingResponse)
@limiter.limit("60/minute")
def save_user_rating(request: Request, body: UserRatingRequest):
    """
    Save user rating for a plan.

    Allows users to rate plans (1-5 stars) and provide feedback.
    """
    try:
        db = get_session()

        session_id = body.plan_id[:36]
        orch = get_orchestrator()
        plan = orch.get_session(session_id)
        if plan:
            for candidate in plan.candidate_plans:
                if candidate.candidate_id == body.plan_id:
                    session_id = plan.session_id
                    break

        user_rating = UserRating(
            id=str(uuid.uuid4()),
            session_id=session_id,
            plan_id=body.plan_id,
            rating=body.rating,
            comment=body.comment,
            rationale=body.rationale,
        )

        db.add(user_rating)
        db.commit()

        return UserRatingResponse(saved=True, rating_id=str(user_rating.id))

    except Exception:
        logger.exception("Unexpected error saving user rating")
        raise HTTPException(
            status_code=500, detail="Operation failed. Please try again."
        )


@router.get("/state/{session_id}", response_model=OptimizationStateResponse)
@limiter.limit("60/minute")
def get_optimization_state(request: Request, session_id: str):
    """
    Get current optimization state for a session.

    Returns the status of ongoing optimization (idle, generating_variants, rating, etc).
    """
    try:
        # For now, return idle state
        # In production, you'd track actual state in cache/database
        return OptimizationStateResponse(
            status="idle", progress=0.0, message="Optimization not started"
        )

    except Exception:
        logger.exception("Unexpected error getting optimization state")
        raise HTTPException(
            status_code=500, detail="Operation failed. Please try again."
        )


@router.post("/manual", response_model=ManualPlanResponse)
@limiter.limit("30/hour")
def submit_manual_plan(request: Request, body: ManualPlanRequest):
    """Normalize, evaluate, and rank a manually supplied plan."""
    try:
        optimizer = get_optimizer_service()
        result = optimizer.submit_manual_plan(
            ManualPlanSubmission(
                session_id=body.session_id,
                title=body.title,
                summary=body.summary,
                plan_text=body.plan_text,
                assumptions=body.assumptions,
                constraints=body.constraints,
                success_criteria=body.success_criteria,
                risks=body.risks,
                fallbacks=body.fallbacks,
                steps=[NormalizedStep(**step.model_dump()) for step in body.steps],
                estimated_time_minutes=body.estimated_time_minutes,
                estimated_cost_usd=body.estimated_cost_usd,
                metadata=body.metadata,
            ),
            judge_models=body.judge_models or None,
        )
        if body.session_id:
            orch = get_orchestrator()
            orch.register_manual_candidate(
                body.session_id,
                ManualPlanSubmission(
                    session_id=body.session_id,
                    title=body.title,
                    summary=body.summary,
                    plan_text=body.plan_text,
                    assumptions=body.assumptions,
                    constraints=body.constraints,
                    success_criteria=body.success_criteria,
                    risks=body.risks,
                    fallbacks=body.fallbacks,
                    steps=[NormalizedStep(**step.model_dump()) for step in body.steps],
                    estimated_time_minutes=body.estimated_time_minutes,
                    estimated_cost_usd=body.estimated_cost_usd,
                    metadata=body.metadata,
                ),
            )
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error submitting manual plan")
        raise HTTPException(status_code=500, detail="Failed to process manual plan.")


@router.post("/normalize", response_model=NormalizePlanResponse)
@limiter.limit("60/minute")
def normalize_plan(request: Request, body: NormalizePlanRequest):
    """Normalize a raw plan payload into the canonical plan structure."""
    try:
        optimizer = get_optimizer_service()
        normalized = optimizer.normalize_plan_payload(
            body.plan,
            session_id=body.session_id,
            source_type=_normalize_source_type(body.source_type),
            source_model=body.source_model,
            planning_style=body.planning_style,
            persist=body.persist,
        )
        return {"normalized_plan": normalized.model_dump(mode="json")}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error normalizing plan")
        raise HTTPException(status_code=500, detail="Failed to normalize plan.")


@router.post("/evaluate", response_model=PlanEvaluationResponse)
@limiter.limit("30/hour")
def evaluate_plans(request: Request, body: PlanEvaluationRequest):
    """Normalize, evaluate, and rank plans using the rubric-based evaluator."""
    try:
        optimizer = get_optimizer_service()
        normalized_plans = [
            optimizer.normalize_plan_payload(
                plan,
                session_id=body.session_id,
                source_model=str(plan.get("source_model") or "unknown"),
                planning_style=str(plan.get("planning_style") or "baseline"),
            )
            for plan in body.plans
        ]
        evaluations = optimizer.evaluate_normalized_plans(
            normalized_plans, body.judge_models or None
        )
        ranking = optimizer.rank_plans(normalized_plans, evaluations)
        return {
            "normalized_plans": [
                plan.model_dump(mode="json") for plan in normalized_plans
            ],
            "evaluations": {
                plan_id: {
                    judge_model: evaluation.model_dump(mode="json")
                    for judge_model, evaluation in plan_evaluations.items()
                }
                for plan_id, plan_evaluations in evaluations.items()
            },
            "ranking": [item.model_dump(mode="json") for item in ranking],
        }
    except Exception:
        logger.exception("Unexpected error evaluating plans")
        raise HTTPException(status_code=500, detail="Failed to evaluate plans.")


@router.post("/compare", response_model=PairwiseComparisonResponse)
@limiter.limit("30/hour")
def compare_plans(request: Request, body: PairwiseComparisonRequest):
    """Normalize, evaluate, compare, and rank multiple candidate plans."""
    try:
        optimizer = get_optimizer_service()
        normalized_plans = [
            optimizer.normalize_plan_payload(
                plan,
                session_id=body.session_id,
                source_model=str(plan.get("source_model") or "unknown"),
                planning_style=str(plan.get("planning_style") or "baseline"),
            )
            for plan in body.plans
        ]
        evaluations = optimizer.evaluate_normalized_plans(
            normalized_plans, body.judge_models or None
        )
        comparisons = optimizer.compare_plans(normalized_plans, evaluations)
        ranking = optimizer.rank_plans(normalized_plans, evaluations)
        return {
            "normalized_plans": [
                plan.model_dump(mode="json") for plan in normalized_plans
            ],
            "evaluations": {
                plan_id: {
                    judge_model: evaluation.model_dump(mode="json")
                    for judge_model, evaluation in plan_evaluations.items()
                }
                for plan_id, plan_evaluations in evaluations.items()
            },
            "comparisons": [item.model_dump(mode="json") for item in comparisons],
            "ranking": [item.model_dump(mode="json") for item in ranking],
        }
    except Exception:
        logger.exception("Unexpected error comparing plans")
        raise HTTPException(status_code=500, detail="Failed to compare plans.")
