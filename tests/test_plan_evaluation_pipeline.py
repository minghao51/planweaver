from unittest.mock import Mock

from planweaver.models.plan import ManualPlanSubmission, PlanSourceType
from planweaver.services.pairwise_comparison_service import PairwiseComparisonService
from planweaver.services.plan_evaluator import PlanEvaluator
from planweaver.services.plan_normalizer import PlanNormalizer


def test_plan_normalizer_builds_manual_plan_from_text():
    normalizer = PlanNormalizer()

    normalized = normalizer.normalize_manual_plan(
        ManualPlanSubmission(
            title="Manual rollout plan",
            plan_text="""
            Audit current deployment
            Prepare a rollback path
            Deploy and validate
            """,
        )
    )

    assert normalized.source_type == PlanSourceType.MANUAL
    assert len(normalized.steps) == 3
    assert "Missing explicit success criteria." in normalized.normalization_warnings
    assert normalized.steps[-1].validation == ["Verify the outcome against the requested goal."]


def test_plan_evaluator_returns_heuristic_rubric_scores():
    normalizer = PlanNormalizer()
    evaluator = PlanEvaluator(llm_gateway=Mock())
    evaluator.llm_gateway.complete.side_effect = RuntimeError("offline")

    plan = normalizer.normalize_generated_plan(
        {
            "id": "plan-1",
            "title": "Generated plan",
            "description": "A structured implementation plan",
            "success_criteria": ["Feature works end-to-end"],
            "risks": ["Migration complexity"],
            "fallbacks": ["Revert to the previous release"],
            "execution_graph": [
                {
                    "step_id": 1,
                    "task": "Capture the current behavior",
                    "validation": ["Record baseline outputs"],
                },
                {
                    "step_id": 2,
                    "task": "Implement the new flow",
                    "dependencies": [1],
                },
            ],
        },
        source_model="test-model",
    )

    evaluations = evaluator.evaluate_plan(plan, ["judge-a"])
    result = evaluations["judge-a"]

    assert result.plan_id == "plan-1"
    assert set(result.rubric_scores) == set(PlanEvaluator.RUBRIC)
    assert result.overall_score > 0
    assert result.verdict.value in {"acceptable", "strong", "weak"}


def test_pairwise_comparison_ranks_higher_scoring_plan_first():
    normalizer = PlanNormalizer()
    evaluator = PlanEvaluator(llm_gateway=Mock())
    evaluator.llm_gateway.complete.side_effect = RuntimeError("offline")
    pairwise = PairwiseComparisonService()

    strong_plan = normalizer.normalize_generated_plan(
        {
            "id": "plan-strong",
            "title": "Strong plan",
            "description": "Plan with validation and fallbacks",
            "success_criteria": ["Ship without regressions"],
            "fallbacks": ["Rollback to previous version"],
            "risks": ["Deployment error"],
            "execution_graph": [
                {
                    "step_id": 1,
                    "task": "Audit current behavior",
                    "validation": ["Capture baseline results"],
                },
                {
                    "step_id": 2,
                    "task": "Implement the change",
                    "dependencies": [1],
                    "validation": ["Run regression tests"],
                },
                {
                    "step_id": 3,
                    "task": "Release gradually",
                    "dependencies": [2],
                    "validation": ["Monitor key metrics"],
                },
            ],
        },
        source_model="planner-a",
    )
    weak_plan = normalizer.normalize_generated_plan(
        {
            "id": "plan-weak",
            "title": "Weak plan",
            "description": "Just do the thing",
            "execution_graph": [{"step_id": 1, "task": "Make the change"}],
        },
        source_model="planner-b",
    )

    evaluations = {
        strong_plan.id: evaluator.evaluate_plan(strong_plan, ["judge-a"]),
        weak_plan.id: evaluator.evaluate_plan(weak_plan, ["judge-a"]),
    }
    comparison = pairwise.compare_pair(
        strong_plan,
        weak_plan,
        evaluations[strong_plan.id],
        evaluations[weak_plan.id],
    )
    ranking = pairwise.rank_plans([strong_plan, weak_plan], evaluations)

    assert comparison.winner_plan_id == strong_plan.id
    assert ranking[0].plan_id == strong_plan.id
    assert ranking[0].rank == 1
