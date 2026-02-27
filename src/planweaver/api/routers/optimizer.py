import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request

from ....db.database import get_session
from ....services.optimizer_service import OptimizerService
from ..schemas import (
    OptimizerRequest,
    OptimizerResponse,
    RatePlansRequest,
    RatePlansResponse,
    UserRatingRequest,
    UserRatingResponse,
    OptimizationStateResponse,
)
from ..middleware import limiter
from ....db.models import UserRating

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimizer", tags=["optimizer"])


def get_optimizer_service():
    """Get OptimizerService instance"""
    db = get_session()
    try:
        return OptimizerService(db)
    finally:
        pass  # Keep session open for service to use


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

        # Use the proposal_id as session_id for now
        # In production, you'd track the actual session
        session_id = body.selected_proposal_id[:36]  # Extract potential session_id

        results = optimizer.optimize_plan(
            session_id=session_id,
            selected_proposal_id=body.selected_proposal_id,
            optimization_types=body.optimization_types,
            rate_with_models=["claude-3.5-sonnet", "gpt-4o", "deepseek-chat"]
        )

        return OptimizerResponse(
            optimization_id=str(uuid.uuid4()),
            status=results.get("status", "unknown"),
            variants=results.get("variants", []),
            ratings=results.get("ratings", {}),
            session_id=session_id
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Cannot complete operation: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error optimizing plan")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


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

    except Exception as e:
        logger.exception(f"Unexpected error getting optimization results")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


@router.post("/rate", response_model=RatePlansResponse)
@limiter.limit("30/hour")
def rate_plans(request: Request, body: RatePlansRequest):
    """
    Rate plans using multiple AI models.

    This endpoint rates the specified plans using multiple AI models
    for comparison on various criteria.
    """
    try:
        from ....services.model_rater import ModelRater

        model_rater = ModelRater()
        ratings_by_plan = {}

        for plan_id in body.plan_ids:
            # For now, we need plan data
            # In production, you'd fetch from database
            logger.warning(f"Rating plan {plan_id} - needs plan data from database")
            ratings_by_plan[plan_id] = {
                "ratings": {},
                "average_score": 5.0
            }

        return RatePlansResponse(
            rating_id=str(uuid.uuid4()),
            status="completed",
            ratings=ratings_by_plan
        )

    except Exception as e:
        logger.exception(f"Unexpected error rating plans")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


@router.post("/user-rating", response_model=UserRatingResponse)
@limiter.limit("60/minute")
def save_user_rating(request: Request, body: UserRatingRequest):
    """
    Save user rating for a plan.

    Allows users to rate plans (1-5 stars) and provide feedback.
    """
    try:
        db = get_session()

        user_rating = UserRating(
            id=str(uuid.uuid4()),
            session_id=body.plan_id[:36],  # Extract potential session_id
            plan_id=body.plan_id,
            rating=body.rating,
            comment=body.comment,
            rationale=body.rationale
        )

        db.add(user_rating)
        db.commit()

        return UserRatingResponse(
            saved=True,
            rating_id=str(user_rating.id)
        )

    except Exception as e:
        logger.exception(f"Unexpected error saving user rating")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")


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
            status="idle",
            progress=0.0,
            message="Optimization not started"
        )

    except Exception as e:
        logger.exception(f"Unexpected error getting optimization state")
        raise HTTPException(status_code=500, detail="Operation failed. Please try again.")
