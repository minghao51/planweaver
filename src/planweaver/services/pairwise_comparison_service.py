from __future__ import annotations

from statistics import mean, pstdev
from typing import Dict, List

from ..models.plan import (
    ComparisonMargin,
    DisagreementLevel,
    NormalizedPlan,
    PairwisePlanComparison,
    PlanEvaluation,
    RankedPlanResult,
)


class PairwiseComparisonService:
    """Compare and rank normalized plans using evaluator outputs."""

    def compare_pair(
        self,
        left_plan: NormalizedPlan,
        right_plan: NormalizedPlan,
        left_evaluations: Dict[str, PlanEvaluation],
        right_evaluations: Dict[str, PlanEvaluation],
    ) -> PairwisePlanComparison:
        left_score = mean(evaluation.overall_score for evaluation in left_evaluations.values())
        right_score = mean(evaluation.overall_score for evaluation in right_evaluations.values())

        if left_score >= right_score:
            winner_plan = left_plan
            winner_score = left_score
            loser_plan = right_plan
            loser_score = right_score
        else:
            winner_plan = right_plan
            winner_score = right_score
            loser_plan = left_plan
            loser_score = left_score

        score_gap = winner_score - loser_score
        margin = self._margin_for_gap(score_gap)

        preference_factors = self._preference_factors(
            left_plan,
            right_plan,
            left_evaluations,
            right_evaluations,
        )

        return PairwisePlanComparison(
            left_plan_id=left_plan.id,
            right_plan_id=right_plan.id,
            judge_model="aggregate",
            winner_plan_id=winner_plan.id,
            margin=margin,
            rationale=(
                f"{winner_plan.title} is preferred over {loser_plan.title} "
                f"because it scored {winner_score:.2f} vs {loser_score:.2f} "
                f"and performed better on {', '.join(preference_factors[:2]) or 'overall execution readiness'}."
            ),
            preference_factors=preference_factors,
        )

    def rank_plans(
        self,
        plans: List[NormalizedPlan],
        evaluations_by_plan: Dict[str, Dict[str, PlanEvaluation]],
    ) -> List[RankedPlanResult]:
        scored = []
        for plan in plans:
            evaluations = evaluations_by_plan.get(plan.id, {})
            if not evaluations:
                continue
            scores = [evaluation.overall_score for evaluation in evaluations.values()]
            avg_score = mean(scores)
            disagreement = self._disagreement_level(scores)
            scored.append(
                {
                    "plan": plan,
                    "final_score": round(avg_score, 2),
                    "confidence": round(
                        mean(evaluation.confidence for evaluation in evaluations.values()),
                        2,
                    ),
                    "disagreement_level": disagreement,
                    "recommendation_reason": self._recommendation_reason(plan, evaluations),
                }
            )

        scored.sort(key=lambda item: item["final_score"], reverse=True)
        return [
            RankedPlanResult(
                plan_id=item["plan"].id,
                final_score=item["final_score"],
                rank=index,
                confidence=item["confidence"],
                disagreement_level=item["disagreement_level"],
                recommendation_reason=item["recommendation_reason"],
            )
            for index, item in enumerate(scored, start=1)
        ]

    def _margin_for_gap(self, gap: float) -> ComparisonMargin:
        if gap >= 1.5:
            return ComparisonMargin.CLEAR
        if gap >= 0.6:
            return ComparisonMargin.MODERATE
        return ComparisonMargin.NARROW

    def _disagreement_level(self, scores: List[float]) -> DisagreementLevel:
        if len(scores) <= 1:
            return DisagreementLevel.LOW
        spread = pstdev(scores)
        if spread >= 1.25:
            return DisagreementLevel.HIGH
        if spread >= 0.6:
            return DisagreementLevel.MEDIUM
        return DisagreementLevel.LOW

    def _recommendation_reason(
        self,
        plan: NormalizedPlan,
        evaluations: Dict[str, PlanEvaluation],
    ) -> str:
        strengths = []
        for evaluation in evaluations.values():
            strengths.extend(evaluation.strengths)
        strongest = strengths[0] if strengths else "balanced rubric performance"
        return f"Recommended because it shows {strongest.lower()}."

    def _preference_factors(
        self,
        left_plan: NormalizedPlan,
        right_plan: NormalizedPlan,
        left_evaluations: Dict[str, PlanEvaluation],
        right_evaluations: Dict[str, PlanEvaluation],
    ) -> List[str]:
        left_avg = self._average_rubric_scores(left_evaluations)
        right_avg = self._average_rubric_scores(right_evaluations)
        deltas = []
        for criterion, left_score in left_avg.items():
            deltas.append((criterion, left_score - right_avg.get(criterion, 0.0)))
        deltas.sort(key=lambda item: abs(item[1]), reverse=True)
        return [criterion for criterion, _ in deltas[:3]]

    def _average_rubric_scores(
        self, evaluations: Dict[str, PlanEvaluation]
    ) -> Dict[str, float]:
        if not evaluations:
            return {}
        rubric_totals: Dict[str, List[float]] = {}
        for evaluation in evaluations.values():
            for criterion, score in evaluation.rubric_scores.items():
                rubric_totals.setdefault(criterion, []).append(score)
        return {
            criterion: mean(scores)
            for criterion, scores in rubric_totals.items()
        }
