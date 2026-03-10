from __future__ import annotations

import json
from statistics import mean
from typing import Dict, List, Optional

from .llm_gateway import LLMGateway
from ..models.plan import EvaluationVerdict, NormalizedPlan, PlanEvaluation


class PlanEvaluator:
    """Evaluate normalized plans with a rubric and optional judge models."""

    DEFAULT_MODELS = ["claude-3.5-sonnet", "gpt-4o", "deepseek-chat"]
    RUBRIC = [
        "completeness",
        "feasibility",
        "constraint_satisfaction",
        "dependency_correctness",
        "risk_coverage",
        "verification_quality",
        "adaptability",
        "cost_realism",
        "time_realism",
        "execution_readiness",
    ]

    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm_gateway = llm_gateway or LLMGateway()

    def evaluate_plan(
        self, plan: NormalizedPlan, judge_models: Optional[List[str]] = None
    ) -> Dict[str, PlanEvaluation]:
        models = judge_models or self.DEFAULT_MODELS
        return {
            model: self._evaluate_with_model(plan, model)
            for model in models
        }

    def aggregate_evaluations(
        self, evaluations: Dict[str, PlanEvaluation]
    ) -> Dict[str, float | str]:
        if not evaluations:
            return {"average_score": 0.0, "confidence": 0.0, "verdict": "reject"}

        overall_scores = [evaluation.overall_score for evaluation in evaluations.values()]
        confidences = [evaluation.confidence for evaluation in evaluations.values()]
        verdict = max(
            (
                evaluation.verdict.value
                for evaluation in evaluations.values()
            ),
            key=lambda current: [
                EvaluationVerdict.REJECT.value,
                EvaluationVerdict.WEAK.value,
                EvaluationVerdict.ACCEPTABLE.value,
                EvaluationVerdict.STRONG.value,
            ].index(current),
        )
        return {
            "average_score": round(mean(overall_scores), 2),
            "confidence": round(mean(confidences), 2),
            "verdict": verdict,
        }

    def _evaluate_with_model(
        self, plan: NormalizedPlan, judge_model: str
    ) -> PlanEvaluation:
        prompt = self._build_evaluation_prompt(plan)

        try:
            response = self.llm_gateway.complete(
                model=judge_model,
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
                max_tokens=2048,
            )
            parsed = json.loads(response["content"])
            return self._coerce_evaluation(plan, judge_model, parsed)
        except Exception:
            return self._heuristic_evaluation(plan, judge_model)

    def _build_evaluation_prompt(self, plan: NormalizedPlan) -> str:
        return f"""Evaluate this normalized execution plan.

Return JSON only with:
- rubric_scores: object with scores from 1.0 to 10.0 for {", ".join(self.RUBRIC)}
- strengths: list of short strings
- weaknesses: list of short strings
- blocking_issues: list of short strings
- confidence: float from 0.0 to 1.0

Plan:
{plan.model_dump_json(indent=2)}
"""

    def _coerce_evaluation(
        self, plan: NormalizedPlan, judge_model: str, payload: Dict[str, object]
    ) -> PlanEvaluation:
        rubric_scores = {
            criterion: float((payload.get("rubric_scores") or {}).get(criterion, 5.0))
            for criterion in self.RUBRIC
        }
        overall_score = round(mean(rubric_scores.values()), 2)
        confidence = float(payload.get("confidence", 0.6))
        verdict = self._verdict_for_score(overall_score, payload.get("blocking_issues") or [])
        return PlanEvaluation(
            plan_id=plan.id,
            judge_model=judge_model,
            rubric_scores=rubric_scores,
            overall_score=overall_score,
            strengths=[str(item) for item in payload.get("strengths", [])][:5],
            weaknesses=[str(item) for item in payload.get("weaknesses", [])][:5],
            blocking_issues=[str(item) for item in payload.get("blocking_issues", [])][:5],
            confidence=max(0.0, min(confidence, 1.0)),
            verdict=verdict,
        )

    def _heuristic_evaluation(
        self, plan: NormalizedPlan, judge_model: str
    ) -> PlanEvaluation:
        step_count = len(plan.steps)
        dependency_ratio = sum(bool(step.dependencies) for step in plan.steps) / max(step_count, 1)
        validation_ratio = sum(bool(step.validation) for step in plan.steps) / max(step_count, 1)

        rubric_scores = {
            "completeness": min(10.0, 4.5 + step_count),
            "feasibility": 8.0 if step_count > 0 else 3.0,
            "constraint_satisfaction": 7.5 if plan.constraints else 6.0,
            "dependency_correctness": round(6.0 + (dependency_ratio * 3.0), 2),
            "risk_coverage": round(6.0 + min(len(plan.risks), 3) * 0.8, 2),
            "verification_quality": round(5.5 + (validation_ratio * 3.5), 2),
            "adaptability": 7.5 if plan.fallbacks else 6.0,
            "cost_realism": 7.5 if plan.estimated_cost_usd is not None else 6.0,
            "time_realism": 7.5 if plan.estimated_time_minutes is not None else 6.0,
            "execution_readiness": 8.0 if step_count >= 2 else 5.5,
        }

        weaknesses: List[str] = []
        blocking_issues: List[str] = []
        if plan.normalization_warnings:
            weaknesses.extend(plan.normalization_warnings)
        if not plan.success_criteria:
            weaknesses.append("Missing explicit success criteria.")
        if not any(step.validation for step in plan.steps):
            blocking_issues.append("No verification steps were defined.")

        overall_score = round(mean(rubric_scores.values()), 2)
        confidence = round(max(0.35, 0.8 - (0.08 * len(plan.normalization_warnings))), 2)

        return PlanEvaluation(
            plan_id=plan.id,
            judge_model=judge_model,
            rubric_scores=rubric_scores,
            overall_score=overall_score,
            strengths=self._heuristic_strengths(plan),
            weaknesses=weaknesses[:5],
            blocking_issues=blocking_issues[:5],
            confidence=confidence,
            verdict=self._verdict_for_score(overall_score, blocking_issues),
        )

    def _heuristic_strengths(self, plan: NormalizedPlan) -> List[str]:
        strengths: List[str] = []
        if len(plan.steps) >= 3:
            strengths.append("The plan has a meaningful execution breakdown.")
        if any(step.validation for step in plan.steps):
            strengths.append("The plan includes verification steps.")
        if plan.risks:
            strengths.append("The plan acknowledges delivery risks.")
        if plan.fallbacks:
            strengths.append("The plan contains fallback options.")
        return strengths[:5]

    def _verdict_for_score(
        self, overall_score: float, blocking_issues: List[str]
    ) -> EvaluationVerdict:
        if blocking_issues:
            return EvaluationVerdict.WEAK if overall_score >= 6.0 else EvaluationVerdict.REJECT
        if overall_score >= 8.5:
            return EvaluationVerdict.STRONG
        if overall_score >= 6.5:
            return EvaluationVerdict.ACCEPTABLE
        if overall_score >= 5.0:
            return EvaluationVerdict.WEAK
        return EvaluationVerdict.REJECT
