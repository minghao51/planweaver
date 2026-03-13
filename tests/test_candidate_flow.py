from unittest.mock import Mock

from src.planweaver.models.plan import ExecutionStep, StepStatus, StrawmanProposal
from src.planweaver.orchestrator import Orchestrator


def _step(
    step_id: int, task: str, dependencies: list[int] | None = None
) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        task=task,
        prompt_template_id="default",
        assigned_model="test-model",
        dependencies=dependencies or [],
        status=StepStatus.PENDING,
    )


def test_start_session_seeds_candidate_and_context_suggestions():
    orchestrator = Orchestrator()
    orchestrator.planner.analyze_intent = Mock(
        return_value={
            "identified_constraints": ["python"],
            "missing_information": [],
            "suggested_approach": "Ship a planning assistant",
            "estimated_complexity": "medium",
        }
    )
    orchestrator.planner.decompose_into_steps = Mock(
        return_value=[_step(1, "Capture the current planning flow")]
    )

    plan = orchestrator.start_session("Refactor a GitHub planning repo")

    assert len(plan.candidate_plans) == 1
    assert plan.candidate_plans[0].normalized_plan_id is not None
    assert plan.context_suggestions
    assert plan.context_suggestions[0].suggestion_type == "github"


def test_select_proposal_creates_candidates_and_approve_candidate_activates_graph():
    orchestrator = Orchestrator()
    orchestrator.planner.analyze_intent = Mock(
        return_value={
            "identified_constraints": [],
            "missing_information": [],
            "suggested_approach": "Use multiple planning styles",
            "estimated_complexity": "medium",
        }
    )
    orchestrator.planner.decompose_into_steps = Mock(
        side_effect=[
            [_step(1, "Seed baseline")],
            [_step(1, "Baseline plan")],
            [_step(1, "Fast plan")],
            [_step(1, "Risk-aware plan")],
            [_step(1, "Cost-aware plan")],
        ]
    )

    plan = orchestrator.start_session("Plan a migration")
    plan.strawman_proposals = [
        StrawmanProposal(
            id="1",
            title="Guided rollout",
            description="Use phased delivery with validation",
        )
    ]
    orchestrator.plan_repository.save(plan)

    updated = orchestrator.select_proposal(plan, "1")

    generated = [
        candidate
        for candidate in updated.candidate_plans
        if candidate.proposal_id == "1"
    ]
    assert {candidate.planning_style for candidate in generated} == {
        "baseline",
        "fast",
        "risk_averse",
        "cost_aware",
    }

    baseline = next(
        candidate for candidate in generated if candidate.planning_style == "baseline"
    )
    approved = orchestrator.approve_candidate(updated, baseline.candidate_id)

    assert approved.approved_candidate_id == baseline.candidate_id
    assert approved.execution_graph
    assert approved.execution_graph[0].task == "Baseline plan"


def test_refine_candidate_updates_execution_graph_and_records_outcomes():
    orchestrator = Orchestrator()
    orchestrator.planner.analyze_intent = Mock(
        return_value={
            "identified_constraints": [],
            "missing_information": [],
            "suggested_approach": "Refine a candidate",
            "estimated_complexity": "medium",
        }
    )
    orchestrator.planner.decompose_into_steps = Mock(
        return_value=[_step(1, "Original step"), _step(2, "Ship result", [1])]
    )

    plan = orchestrator.start_session("Improve candidate refinement")
    active_candidate = plan.candidate_plans[0]
    orchestrator.approve_candidate(plan, active_candidate.candidate_id)

    updated_candidate = orchestrator.refine_candidate(
        plan,
        active_candidate.candidate_id,
        "edit_step",
        step_id=1,
        task="Updated step",
    )

    assert updated_candidate.execution_graph[0].task == "Updated step"
    assert plan.execution_graph[0].task == "Updated step"
    assert any(
        outcome.event_type == "candidate_refined" for outcome in plan.planning_outcomes
    )
    assert any(
        revision.revision_type == "edit_step" for revision in plan.candidate_revisions
    )
