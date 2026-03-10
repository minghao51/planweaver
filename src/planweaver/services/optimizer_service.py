from typing import List, Dict, Any, Literal, Optional
from logging import getLogger
from sqlalchemy.orm import Session
from .variant_generator import VariantGenerator
from .model_rater import ModelRater
from .plan_evaluator import PlanEvaluator
from .plan_normalizer import PlanNormalizer
from .pairwise_comparison_service import PairwiseComparisonService
from ..db.models import (
    NormalizedPlanRecord,
    OptimizedVariant,
    PairwiseComparisonRecord,
    PlanEvaluationRecord,
    PlanRating,
)
from ..db.repositories import PlanRepository
from ..models.plan import (
    ManualPlanSubmission,
    NormalizedPlan,
    PairwisePlanComparison,
    PlanEvaluation,
    PlanSourceType,
    RankedPlanResult,
)
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
        self.plan_normalizer = PlanNormalizer()
        self.plan_evaluator = PlanEvaluator()
        self.pairwise_comparison = PairwiseComparisonService()
        self.plan_repo = PlanRepository(db)

    def optimize_plan(
        self,
        session_id: str,
        selected_proposal_id: str,
        optimization_types: List[Literal["simplified", "enhanced", "cost-optimized"]]
        | None = None,
        rate_with_models: List[str] | None = None,
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
            "status": "completed",
        }

        # Generate variants
        try:
            for variant_type in optimization_types:
                variant = self._generate_and_save_variant(
                    session_id, selected_proposal_id, proposal, variant_type
                )
                results["variants"].append(variant)
                logger.info(f"Generated {variant_type} variant: {variant['id']}")
        except Exception as e:
            logger.error(f"Failed to generate variants: {e}")
            results["status"] = "partial"
            results["error"] = str(e)

        # Rate all plans (original + variants)
        try:
            plan_ids_to_rate = [selected_proposal_id] + [
                v["id"] for v in results["variants"]
            ]
            results["ratings"] = self._rate_and_save_plans(
                session_id,
                plan_ids_to_rate,
                proposal,  # Original proposal for reference
                results["variants"],
                rate_with_models,
            )
            logger.info(
                f"Rated {len(plan_ids_to_rate)} plans with {len(rate_with_models)} models"
            )
        except Exception as e:
            logger.error(f"Failed to rate plans: {e}")
            results["status"] = "partial"
            results["rating_error"] = str(e)

        return results

    def submit_manual_plan(
        self,
        submission: ManualPlanSubmission,
        judge_models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        normalized = self.plan_normalizer.normalize_manual_plan(submission)
        self._save_normalized_plan(normalized)
        evaluations = self.evaluate_normalized_plans([normalized], judge_models)
        ranking = self.rank_plans([normalized], evaluations)
        return {
            "normalized_plan": normalized.model_dump(mode="json"),
            "evaluations": self._serialize_evaluations(evaluations[normalized.id]),
            "ranking": [item.model_dump(mode="json") for item in ranking],
        }

    def normalize_plan_payload(
        self,
        plan_data: Dict[str, Any],
        *,
        session_id: Optional[str] = None,
        source_type: PlanSourceType = PlanSourceType.LLM_GENERATED,
        source_model: str = "unknown",
        planning_style: str = "baseline",
        persist: bool = True,
    ) -> NormalizedPlan:
        normalized = self.plan_normalizer.normalize_generated_plan(
            plan_data,
            session_id=session_id,
            source_type=source_type,
            source_model=source_model,
            planning_style=planning_style,
        )
        if persist:
            self._save_normalized_plan(normalized)
        return normalized

    def evaluate_normalized_plans(
        self,
        plans: List[NormalizedPlan],
        judge_models: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, PlanEvaluation]]:
        evaluations_by_plan: Dict[str, Dict[str, PlanEvaluation]] = {}
        for plan in plans:
            evaluations = self.plan_evaluator.evaluate_plan(plan, judge_models)
            self._save_evaluations(plan.session_id, evaluations)
            evaluations_by_plan[plan.id] = evaluations
        return evaluations_by_plan

    def compare_plans(
        self,
        plans: List[NormalizedPlan],
        evaluations_by_plan: Dict[str, Dict[str, PlanEvaluation]],
    ) -> List[PairwisePlanComparison]:
        comparisons: List[PairwisePlanComparison] = []
        for index, left_plan in enumerate(plans):
            for right_plan in plans[index + 1 :]:
                comparison = self.pairwise_comparison.compare_pair(
                    left_plan,
                    right_plan,
                    evaluations_by_plan.get(left_plan.id, {}),
                    evaluations_by_plan.get(right_plan.id, {}),
                )
                self._save_pairwise_comparison(left_plan.session_id, comparison)
                comparisons.append(comparison)
        return comparisons

    def rank_plans(
        self,
        plans: List[NormalizedPlan],
        evaluations_by_plan: Dict[str, Dict[str, PlanEvaluation]],
    ) -> List[RankedPlanResult]:
        return self.pairwise_comparison.rank_plans(plans, evaluations_by_plan)

    def get_normalized_plans(self, session_id: str) -> List[Dict[str, Any]]:
        records = (
            self.db.query(NormalizedPlanRecord)
            .filter(NormalizedPlanRecord.session_id == session_id)
            .all()
        )
        return [record.to_dict() for record in records]

    def _get_proposal(self, session_id: str, proposal_id: str) -> Dict[str, Any] | None:
        """Get proposal from session"""
        session = self.plan_repo.get(session_id)
        if not session:
            return None

        # Find the proposal in strawman_proposals
        for prop in session.strawman_proposals:
            if hasattr(prop, "model_dump"):
                prop_data = prop.model_dump()
            else:
                prop_data = prop

            if (
                prop_data.get("id") == proposal_id
                or prop_data.get("proposal_id") == proposal_id
            ):
                return prop_data

        return None

    def _generate_and_save_variant(
        self,
        session_id: str,
        proposal_id: str,
        proposal: Dict[str, Any],
        variant_type: str,
    ) -> Dict[str, Any]:
        """Generate variant and save to database"""
        # Generate the variant
        variant_data = self.variant_generator.generate_variant(
            proposal=proposal, variant_type=variant_type
        )

        # Save to database
        db_variant = OptimizedVariant(
            id=str(uuid.uuid4()),
            session_id=session_id,
            proposal_id=proposal_id,
            variant_type=variant_type,
            execution_graph=variant_data.get("execution_graph", []),
            variant_metadata=variant_data.get("metadata", {}),
        )
        self.db.add(db_variant)
        self.db.commit()

        return {
            "id": str(db_variant.id),
            "type": variant_type,
            "execution_graph": db_variant.execution_graph,
            "metadata": db_variant.variant_metadata,
        }

    def _rate_and_save_plans(
        self,
        session_id: str,
        plan_ids: List[str],
        original_proposal: Dict[str, Any],
        variants: List[Dict[str, Any]],
        models: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Rate all plans and save to database"""
        ratings_by_plan = {}

        for plan_id in plan_ids:
            # Get plan data
            plan_data = self._get_plan_data(plan_id, original_proposal, variants)

            # Rate with all models
            model_ratings = self.model_rater.rate_plan(plan=plan_data, models=models)

            # Save each model's rating to database
            for model_name, rating in model_ratings.items():
                db_rating = PlanRating(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    plan_id=plan_id,
                    model_name=model_name,
                    ratings=rating.get("ratings", {}),
                    reasoning=rating.get("reasoning", ""),
                )
                self.db.add(db_rating)

            self.db.commit()

            # Calculate average score
            avg_score = sum(
                r.get("overall_score", 5.0) for r in model_ratings.values()
            ) / len(model_ratings)

            ratings_by_plan[plan_id] = {
                "ratings": model_ratings,
                "average_score": round(avg_score, 2),
            }

        return ratings_by_plan

    def _get_plan_data(
        self,
        plan_id: str,
        original_proposal: Dict[str, Any],
        variants: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Get plan data for rating"""
        # Check if it's the original proposal
        if plan_id == original_proposal.get("id") or plan_id == original_proposal.get(
            "proposal_id"
        ):
            return original_proposal

        # Check if it's a variant
        for variant in variants:
            if variant["id"] == plan_id:
                return {
                    "id": plan_id,
                    "title": f"{variant['type'].title()} Variant",
                    "description": f"Optimized variant with type: {variant['type']}",
                    "execution_graph": variant["execution_graph"],
                    "metadata": variant.get("metadata", {}),
                }

        # Plan not found
        raise ValueError(f"Plan {plan_id} not found")

    def get_optimization_results(self, session_id: str) -> Dict[str, Any]:
        """Retrieve optimization results for a session"""
        # Get variants
        variants = (
            self.db.query(OptimizedVariant)
            .filter(OptimizedVariant.session_id == session_id)
            .all()
        )

        # Get ratings
        ratings = (
            self.db.query(PlanRating).filter(PlanRating.session_id == session_id).all()
        )
        normalized_plans = (
            self.db.query(NormalizedPlanRecord)
            .filter(NormalizedPlanRecord.session_id == session_id)
            .all()
        )
        evaluations = (
            self.db.query(PlanEvaluationRecord)
            .filter(PlanEvaluationRecord.session_id == session_id)
            .all()
        )
        pairwise = (
            self.db.query(PairwiseComparisonRecord)
            .filter(PairwiseComparisonRecord.session_id == session_id)
            .all()
        )

        return {
            "session_id": session_id,
            "variants": [
                v.to_dict()
                if hasattr(v, "to_dict")
                else {
                    "id": str(v.id),
                    "proposal_id": str(v.proposal_id),
                    "variant_type": v.variant_type,
                    "execution_graph": v.execution_graph,
                    "metadata": v.variant_metadata,
                }
                for v in variants
            ],
            "ratings": [
                {
                    "id": str(r.id),
                    "plan_id": str(r.plan_id),
                    "model_name": r.model_name,
                    "ratings": r.ratings,
                    "reasoning": r.reasoning,
                }
                for r in ratings
            ],
            "normalized_plans": [record.to_dict() for record in normalized_plans],
            "evaluations": [record.to_dict() for record in evaluations],
            "pairwise_comparisons": [record.to_dict() for record in pairwise],
        }

    def _save_normalized_plan(self, plan: NormalizedPlan) -> None:
        record = self.db.query(NormalizedPlanRecord).filter_by(id=plan.id).first()
        payload = {
            "session_id": plan.session_id,
            "source_type": plan.source_type.value,
            "source_model": plan.source_model,
            "planning_style": plan.planning_style,
            "title": plan.title,
            "normalized_payload": plan.model_dump(mode="json"),
            "normalization_warnings": plan.normalization_warnings,
        }
        if record:
            for field, value in payload.items():
                setattr(record, field, value)
        else:
            self.db.add(NormalizedPlanRecord(id=plan.id, **payload))
        self.db.commit()

    def _save_evaluations(
        self, session_id: Optional[str], evaluations: Dict[str, PlanEvaluation]
    ) -> None:
        for evaluation in evaluations.values():
            self.db.add(
                PlanEvaluationRecord(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    plan_id=evaluation.plan_id,
                    judge_model=evaluation.judge_model,
                    rubric_scores=evaluation.rubric_scores,
                    overall_score=evaluation.overall_score,
                    strengths=evaluation.strengths,
                    weaknesses=evaluation.weaknesses,
                    blocking_issues=evaluation.blocking_issues,
                    confidence=evaluation.confidence,
                    verdict=evaluation.verdict.value,
                )
            )
        self.db.commit()

    def _save_pairwise_comparison(
        self, session_id: Optional[str], comparison: PairwisePlanComparison
    ) -> None:
        self.db.add(
            PairwiseComparisonRecord(
                id=str(uuid.uuid4()),
                session_id=session_id,
                left_plan_id=comparison.left_plan_id,
                right_plan_id=comparison.right_plan_id,
                judge_model=comparison.judge_model,
                winner_plan_id=comparison.winner_plan_id,
                margin=comparison.margin.value,
                rationale=comparison.rationale,
                preference_factors=comparison.preference_factors,
            )
        )
        self.db.commit()

    def _serialize_evaluations(
        self, evaluations: Dict[str, PlanEvaluation]
    ) -> Dict[str, Any]:
        return {
            judge_model: evaluation.model_dump(mode="json")
            for judge_model, evaluation in evaluations.items()
        }
