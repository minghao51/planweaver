from unittest.mock import Mock, patch, AsyncMock

import pytest

from planweaver.models.plan import CandidatePlan, CandidatePlanStatus, ExecutionStep, Plan, PlanSourceType, PlanStatus
from planweaver.orchestrator import Orchestrator


@pytest.fixture
def orchestrator_with_mocks():
    with (
        patch("planweaver.orchestrator.Planner") as planner_cls,
        patch("planweaver.orchestrator.ExecutionRouter") as router_cls,
    ):
        planner = Mock()
        planner.create_initial_plan.return_value = Plan(user_intent="Test intent")
        planner.generate_strawman_proposals.return_value = []
        planner.refine_plan.return_value = Plan(user_intent="Test intent")
        planner_cls.return_value = planner

        router = Mock()
        router.execute_plan = AsyncMock()
        router_cls.return_value = router

        orchestrator = Orchestrator()
        yield orchestrator, planner, router


def test_start_session_stores_only_explicit_overrides(orchestrator_with_mocks):
    orchestrator, planner, _ = orchestrator_with_mocks

    plan = orchestrator.start_session(
        "Test intent",
        planner_model="planner-override",
        executor_model="executor-override",
    )

    planner.create_initial_plan.assert_called_once()
    _, kwargs = planner.create_initial_plan.call_args
    assert kwargs["user_intent"] == "Test intent"
    assert kwargs["scenario_name"] is None
    assert kwargs["model"] == "planner-override"
    assert plan.planner_model == "planner-override"
    assert plan.executor_model == "executor-override"


def test_start_session_without_overrides_keeps_override_fields_empty(
    orchestrator_with_mocks,
):
    orchestrator, planner, _ = orchestrator_with_mocks

    plan = orchestrator.start_session("Test intent")

    planner.create_initial_plan.assert_called_once()
    _, kwargs = planner.create_initial_plan.call_args
    assert kwargs["user_intent"] == "Test intent"
    assert kwargs["scenario_name"] is None
    assert kwargs["model"] == orchestrator.planner_model
    assert plan.planner_model is None
    assert plan.executor_model is None


def test_follow_up_planner_calls_use_plan_override(orchestrator_with_mocks):
    orchestrator, planner, _ = orchestrator_with_mocks
    plan = Plan(user_intent="Test intent", planner_model="planner-override")

    orchestrator.get_strawman_proposals(plan)
    planner.generate_strawman_proposals.assert_called_once_with(
        "Test intent",
        plan=None,
        model="planner-override",
    )

    orchestrator.answer_questions(plan, {})
    planner.refine_plan.assert_called_once_with(
        plan=plan,
        user_answers={},
        model="planner-override",
    )


@pytest.mark.asyncio
async def test_execute_uses_executor_override_when_present(orchestrator_with_mocks):
    orchestrator, _, router = orchestrator_with_mocks
    plan = Plan(
        user_intent="Test intent",
        status=PlanStatus.APPROVED,
        executor_model="executor-override",
    )
    router.execute_plan.return_value = plan

    await orchestrator.execute(plan, {"k": "v"})

    router.execute_plan.assert_awaited_once_with(
        plan=plan,
        context={"k": "v"},
        model_override="executor-override",
        observer=orchestrator.observer,
        observer_drift_threshold=0.8,
    )


@pytest.mark.asyncio
async def test_execute_uses_step_assigned_models_as_fallback(orchestrator_with_mocks):
    orchestrator, _, router = orchestrator_with_mocks
    plan = Plan(user_intent="Test intent", status=PlanStatus.APPROVED, executor_model=None)
    router.execute_plan.return_value = plan

    await orchestrator.execute(plan)

    router.execute_plan.assert_awaited_once_with(
        plan=plan,
        context={},
        model_override=None,
        observer=orchestrator.observer,
        observer_drift_threshold=0.8,
    )


@pytest.mark.asyncio
async def test_execute_replans_when_observer_signal_is_present(orchestrator_with_mocks):
    orchestrator, planner, router = orchestrator_with_mocks

    candidate = CandidatePlan(
        session_id="test-session",
        title="Approved candidate",
        summary="Baseline",
        source_type=PlanSourceType.LLM_GENERATED,
        source_model="planner-model",
        status=CandidatePlanStatus.APPROVED,
        execution_graph=[
            ExecutionStep(
                step_id=1,
                task="Generate output",
                prompt_template_id="default",
                assigned_model="executor-model",
                output="bad output",
                status="COMPLETED",
            ),
            ExecutionStep(
                step_id=2,
                task="Use output",
                prompt_template_id="default",
                assigned_model="executor-model",
                dependencies=[1],
            ),
        ],
    )
    plan = Plan(
        session_id="test-session",
        user_intent="Test intent",
        status=PlanStatus.APPROVED,
        approved_candidate_id=candidate.candidate_id,
        selected_candidate_id=candidate.candidate_id,
        candidate_plans=[candidate],
        execution_graph=[ExecutionStep(**step.model_dump()) for step in candidate.execution_graph],
    )
    plan.metadata["observer_signal"] = {
        "step_id": 1,
        "drift_description": "The step output contains failure-like language despite reporting success.",
    }

    replanned_steps = [
        ExecutionStep(
            step_id=1,
            task="Generate output (refined)",
            prompt_template_id="default",
            assigned_model="executor-model",
            dependencies=[],
        ),
        ExecutionStep(
            step_id=2,
            task="Use refined output",
            prompt_template_id="default",
            assigned_model="executor-model",
            dependencies=[1],
        ),
    ]
    planner.regenerate_steps_from_point.return_value = replanned_steps

    first_result = Plan.model_validate(plan.model_dump(mode="json"))

    async def execute_side_effect(**kwargs):
        current_plan = kwargs["plan"]
        if current_plan.metadata.get("observer_replan_count", 0) == 0:
            return first_result

        current_plan.metadata.pop("observer_signal", None)
        current_plan.execution_graph = [ExecutionStep(**step.model_dump()) for step in replanned_steps]
        current_plan.status = PlanStatus.COMPLETED
        current_plan.final_output = {"step_2": "done"}
        return current_plan

    router.execute_plan = AsyncMock(side_effect=execute_side_effect)

    result = await orchestrator.execute(plan)

    assert planner.regenerate_steps_from_point.called
    assert result.status == PlanStatus.COMPLETED
    assert result.metadata["observer_replan_count"] == 1
    assert result.execution_graph[0].task == "Generate output (refined)"
    assert any(outcome.event_type == "observer_replan_triggered" for outcome in result.planning_outcomes)


@pytest.mark.asyncio
async def test_execute_fails_when_observer_replan_limit_is_reached(orchestrator_with_mocks):
    orchestrator, _, router = orchestrator_with_mocks
    plan = Plan(
        user_intent="Test intent",
        status=PlanStatus.APPROVED,
        metadata={
            "observer_signal": {"step_id": 1, "drift_description": "Repeated drift"},
            "observer_replan_count": 1,
            "max_replans_per_session": 1,
        },
    )
    router.execute_plan = AsyncMock(return_value=plan)

    result = await orchestrator.execute(plan)

    assert result.status == PlanStatus.FAILED
    assert any(outcome.event_type == "observer_replan_limit_reached" for outcome in result.planning_outcomes)
