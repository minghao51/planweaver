from typing import List, Dict, Any, Literal
from logging import getLogger
from sqlalchemy.orm import Session
from .variant_generator import VariantGenerator
from .model_rater import ModelRater
from ..db.models import OptimizedVariant, PlanRating
from ..db.repositories import PlanRepository
import uuid

logger = getLogger(__name__)


class OptimizerService:
    """
    Orchestrates plan optimization:
    - Generates optimized variants
    - Rates plans (original + variants) with multiple models
    - Manages database persistence
    """

    def __init__(self, db: Session):
        self.db = db
        self.variant_generator = VariantGenerator()
        self.model_rater = ModelRater()
        self.plan_repo = PlanRepository(db)

    def optimize_plan(
        self,
        session_id: str,
        selected_proposal_id: str,
        optimization_types: List[Literal["simplified", "enhanced", "cost-optimized"]] | None = None,
        rate_with_models: List[str] | None = None
    ) -> Dict[str, Any]:
        """
        Main optimization workflow:
        1. Generate variants
        2. Rate all plans (original + variants)
        3. Persist to database

        Args:
            session_id: Session identifier
            selected_proposal_id: Selected proposal to optimize
            optimization_types: Types of variants to generate
            rate_with_models: Models to use for rating

        Returns:
            Dict with optimization results
        """
        if optimization_types is None:
            optimization_types = ["simplified", "enhanced"]

        if rate_with_models is None:
            rate_with_models = ["claude-3.5-sonnet", "gpt-4o", "deepseek-chat"]

        logger.info(
            f"Starting optimization for session {session_id}, "
            f"proposal {selected_proposal_id}, "
            f"types: {optimization_types}"
        )

        # Get the selected proposal
        proposal = self._get_proposal(session_id, selected_proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {selected_proposal_id} not found")

        results = {
            "session_id": session_id,
            "selected_proposal_id": selected_proposal_id,
            "variants": [],
            "ratings": {},
            "status": "completed"
        }

        # Generate variants
        try:
            for variant_type in optimization_types:
                variant = self._generate_and_save_variant(
                    session_id,
                    selected_proposal_id,
                    proposal,
                    variant_type
                )
                results["variants"].append(variant)
                logger.info(f"Generated {variant_type} variant: {variant['id']}")
        except Exception as e:
            logger.error(f"Failed to generate variants: {e}")
            results["status"] = "partial"
            results["error"] = str(e)

        # Rate all plans (original + variants)
        try:
            plan_ids_to_rate = [selected_proposal_id] + [v["id"] for v in results["variants"]]
            results["ratings"] = self._rate_and_save_plans(
                session_id,
                plan_ids_to_rate,
                proposal,  # Original proposal for reference
                results["variants"],
                rate_with_models
            )
            logger.info(f"Rated {len(plan_ids_to_rate)} plans with {len(rate_with_models)} models")
        except Exception as e:
            logger.error(f"Failed to rate plans: {e}")
            results["status"] = "partial"
            results["rating_error"] = str(e)

        return results

    def _get_proposal(self, session_id: str, proposal_id: str) -> Dict[str, Any] | None:
        """Get proposal from session"""
        session = self.plan_repo.get(session_id)
        if not session:
            return None

        # Find the proposal in strawman_proposals
        for prop in session.strawman_proposals:
            if prop.get("id") == proposal_id or prop.get("proposal_id") == proposal_id:
                return prop

        return None

    def _generate_and_save_variant(
        self,
        session_id: str,
        proposal_id: str,
        proposal: Dict[str, Any],
        variant_type: str
    ) -> Dict[str, Any]:
        """Generate variant and save to database"""
        # Generate the variant
        variant_data = self.variant_generator.generate_variant(
            proposal=proposal,
            variant_type=variant_type
        )

        # Save to database
        db_variant = OptimizedVariant(
            id=str(uuid.uuid4()),
            session_id=session_id,
            proposal_id=proposal_id,
            variant_type=variant_type,
            execution_graph=variant_data.get("execution_graph", []),
            variant_metadata=variant_data.get("metadata", {})
        )
        self.db.add(db_variant)
        self.db.commit()

        return {
            "id": str(db_variant.id),
            "type": variant_type,
            "execution_graph": db_variant.execution_graph,
            "metadata": db_variant.variant_metadata
        }

    def _rate_and_save_plans(
        self,
        session_id: str,
        plan_ids: List[str],
        original_proposal: Dict[str, Any],
        variants: List[Dict[str, Any]],
        models: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Rate all plans and save to database"""
        ratings_by_plan = {}

        for plan_id in plan_ids:
            # Get plan data
            plan_data = self._get_plan_data(plan_id, original_proposal, variants)

            # Rate with all models
            model_ratings = self.model_rater.rate_plan(
                plan=plan_data,
                models=models
            )

            # Save each model's rating to database
            for model_name, rating in model_ratings.items():
                db_rating = PlanRating(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    plan_id=plan_id,
                    model_name=model_name,
                    ratings=rating.get("ratings", {}),
                    reasoning=rating.get("reasoning", "")
                )
                self.db.add(db_rating)

            self.db.commit()

            # Calculate average score
            avg_score = sum(
                r.get("overall_score", 5.0)
                for r in model_ratings.values()
            ) / len(model_ratings)

            ratings_by_plan[plan_id] = {
                "ratings": model_ratings,
                "average_score": round(avg_score, 2)
            }

        return ratings_by_plan

    def _get_plan_data(
        self,
        plan_id: str,
        original_proposal: Dict[str, Any],
        variants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get plan data for rating"""
        # Check if it's the original proposal
        if plan_id == original_proposal.get("id") or plan_id == original_proposal.get("proposal_id"):
            return original_proposal

        # Check if it's a variant
        for variant in variants:
            if variant["id"] == plan_id:
                return {
                    "id": plan_id,
                    "title": f"{variant['type'].title()} Variant",
                    "description": f"Optimized variant with type: {variant['type']}",
                    "execution_graph": variant["execution_graph"],
                    "metadata": variant.get("metadata", {})
                }

        # Plan not found
        raise ValueError(f"Plan {plan_id} not found")

    def get_optimization_results(self, session_id: str) -> Dict[str, Any]:
        """Retrieve optimization results for a session"""
        # Get variants
        variants = self.db.query(OptimizedVariant).filter(
            OptimizedVariant.session_id == session_id
        ).all()

        # Get ratings
        ratings = self.db.query(PlanRating).filter(
            PlanRating.session_id == session_id
        ).all()

        return {
            "session_id": session_id,
            "variants": [v.to_dict() if hasattr(v, 'to_dict') else {
                "id": str(v.id),
                "proposal_id": str(v.proposal_id),
                "variant_type": v.variant_type,
                "execution_graph": v.execution_graph,
                "metadata": v.variant_metadata
            } for v in variants],
            "ratings": [{
                "id": str(r.id),
                "plan_id": str(r.plan_id),
                "model_name": r.model_name,
                "ratings": r.ratings,
                "reasoning": r.reasoning
            } for r in ratings]
        }
