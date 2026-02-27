from unittest.mock import Mock, patch, AsyncMock

import pytest

from planweaver.models.plan import Plan, PlanStatus
from planweaver.orchestrator import Orchestrator


@pytest.fixture
def orchestrator_with_mocks():
    with patch("planweaver.orchestrator.Planner") as planner_cls, patch("planweaver.orchestrator.ExecutionRouter") as router_cls:
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

    planner.create_initial_plan.assert_called_once_with(
        user_intent="Test intent",
        scenario_name=None,
        model="planner-override",
    )
    assert plan.planner_model == "planner-override"
    assert plan.executor_model == "executor-override"


def test_start_session_without_overrides_keeps_override_fields_empty(orchestrator_with_mocks):
    orchestrator, planner, _ = orchestrator_with_mocks

    plan = orchestrator.start_session("Test intent")

    planner.create_initial_plan.assert_called_once_with(
        user_intent="Test intent",
        scenario_name=None,
        model=orchestrator.planner_model,
    )
    assert plan.planner_model is None
    assert plan.executor_model is None


def test_follow_up_planner_calls_use_plan_override(orchestrator_with_mocks):
    orchestrator, planner, _ = orchestrator_with_mocks
    plan = Plan(user_intent="Test intent", planner_model="planner-override")

    orchestrator.get_strawman_proposals(plan)
    planner.generate_strawman_proposals.assert_called_once_with(
        "Test intent",
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
    plan = Plan(user_intent="Test intent", status=PlanStatus.APPROVED, executor_model="executor-override")
    router.execute_plan.return_value = plan

    await orchestrator.execute(plan, {"k": "v"})

    router.execute_plan.assert_awaited_once_with(
        plan=plan,
        context={"k": "v"},
        model_override="executor-override",
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
    )
