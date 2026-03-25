"""Ensemble planning service (Pattern 3)"""

from __future__ import annotations

import asyncio
from typing import List, Dict, Any, Optional
import logging

from .llm_gateway import LLMGateway
from .planner import Planner
from .plan_evaluator import PlanEvaluator
from .pairwise_comparison_service import PairwiseComparisonService
from .plan_normalizer import PlanNormalizer
from ..models.plan import CandidatePlan, PlanSourceType, NormalizedPlan

logger = logging.getLogger(__name__)


class EnsembleService:
    """Runs 3+ planners in parallel with tournament selection (Pattern 3)"""

    DEFAULT_MODELS = ["claude-3.5-sonnet", "gpt-4o", "deepseek-chat"]

    def __init__(
        self,
        llm_gateway: LLMGateway,
        planner: Planner,
        evaluator: PlanEvaluator,
        comparison_service: PairwiseComparisonService,
        plan_normalizer: PlanNormalizer,
    ):
        self.llm = llm_gateway
        self.planner = planner
        self.evaluator = evaluator
        self.comparison = comparison_service
        self.normalizer = plan_normalizer

    async def run_ensemble(
        self,
        user_intent: str,
        models: Optional[List[str]] = None,
        locked_constraints: Optional[Dict[str, Any]] = None,
        scenario_name: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[NormalizedPlan]:
        """Run 3+ planners in parallel, evaluate with tournament selection"""
        models = models or self.DEFAULT_MODELS
        locked_constraints = locked_constraints or {}

        # 1. Generate candidates in parallel
        tasks = [self._generate_candidate(user_intent, locked_constraints, scenario_name, model) for model in models]
        candidate_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 2. Convert to CandidatePlan objects
        candidates: List[CandidatePlan] = []
        for model, result in zip(models, candidate_results):
            if isinstance(result, Exception):
                logger.error(f"Model {model} failed: {result}")
                continue
            if result is not None:
                assert not isinstance(result, BaseException)
                candidates.append(result)

        if not candidates:
            logger.warning("No candidates generated successfully")
            return None

        # 3. Normalize plans
        normalized = []
        for candidate in candidates:
            try:
                norm_plan = self.normalizer.normalize_generated_plan(
                    {
                        "id": candidate.candidate_id,
                        "title": candidate.title,
                        "summary": candidate.summary,
                        "execution_graph": [step.model_dump() for step in candidate.execution_graph],
                        "metadata": candidate.metadata,
                    },
                    session_id=session_id,
                    source_type=candidate.source_type,
                    source_model=candidate.source_model,
                    planning_style=candidate.planning_style,
                )
                normalized.append(norm_plan)
            except Exception as e:
                logger.error(f"Failed to normalize candidate {candidate.candidate_id}: {e}")

        if not normalized:
            logger.warning("No plans normalized successfully")
            return None

        # 4. Evaluate with multi-model rubric
        evaluations_by_plan = {}
        for norm_plan in normalized:
            evaluations = self.evaluator.evaluate_plan(norm_plan, judge_models=models)
            evaluations_by_plan[norm_plan.id] = evaluations

        # 5. Tournament ranking
        ranked = self.comparison.rank_plans(normalized, evaluations_by_plan)

        if not ranked:
            logger.warning("No ranked plans returned")
            return None

        # Return the winner
        winner_id = ranked[0].plan_id
        for plan in normalized:
            if plan.id == winner_id:
                return plan

        return normalized[0] if normalized else None

    async def _generate_candidate(
        self,
        user_intent: str,
        locked_constraints: Dict[str, Any],
        scenario_name: Optional[str],
        model: str,
    ) -> Optional[CandidatePlan]:
        """Generate a candidate plan from a single model"""
        try:
            steps = self.planner.decompose_into_steps(
                user_intent,
                locked_constraints,
                scenario_name,
                model=model,
            )

            if not isinstance(steps, list):
                logger.warning(f"Model {model} did not return a list of steps")
                return None

            return CandidatePlan(
                title=f"Candidate from {model}",
                summary=user_intent,
                source_type=PlanSourceType.LLM_GENERATED,
                source_model=model,
                planning_style="baseline",
                execution_graph=steps,
                metadata={"ensemble_model": model},
            )
        except Exception as e:
            logger.error(f"Error generating candidate from {model}: {e}")
            return None
