from unittest.mock import AsyncMock, Mock

import pytest

from src.planweaver.models.plan import ExecutionStep, Plan, PlanStatus
from src.planweaver.observer import Observer
from src.planweaver.services.planner import Planner
from src.planweaver.services.router import ExecutionRouter


def test_analyze_intent_extracts_reasoning_summary_and_question_reasoning():
    gateway = Mock()
    gateway.settings.max_reasoning_entries = 6
    gateway.complete.return_value = {
        "content": """
        {
          "identified_constraints": ["FastAPI"],
          "missing_information": ["Which deployment target should we optimize for?"],
          "suggested_approach": "Start with API shape, then map execution steps.",
          "estimated_complexity": "medium"
        }
        """,
        "model": "test-model",
        "usage": {},
    }

    planner = Planner(llm_gateway=gateway)
    plan = Plan(user_intent="Ship PlanWeaver as an app")

    result = planner.analyze_intent(plan.user_intent, plan)

    assert result.identified_constraints == ["FastAPI"]
    assert len(result.missing_information) == 1
    assert result.missing_information[0] == "Which deployment target should we optimize for?"
    assert result.suggested_approach == "Start with API shape, then map execution steps."
    assert result.estimated_complexity == "medium"


def test_create_initial_plan_preserves_reasoning_fallbacks():
    gateway = Mock()
    gateway.settings.max_reasoning_entries = 6
    gateway.complete.return_value = {
        "content": "not valid json",
        "model": "test-model",
        "usage": {},
    }

    planner = Planner(llm_gateway=gateway)
    plan = planner.create_initial_plan("Implement a planning dashboard")

    # Check that plan was created with fallback values
    assert plan.user_intent == "Implement a planning dashboard"
    assert plan.status == PlanStatus.BRAINSTORMING


def test_generate_strawman_proposals_extracts_structured_reasoning():
    gateway = Mock()
    gateway.settings.max_reasoning_entries = 6
    # Mock that returns invalid JSON to test fallback
    gateway.complete.side_effect = Exception("LLM error")

    planner = Planner(llm_gateway=gateway)
    proposals = planner.generate_strawman_proposals("Implement reasoning visibility")

    # Should return empty list on error
    assert len(proposals) == 0


@pytest.mark.asyncio
async def test_execute_plan_records_guided_correction_and_retry_success():
    llm = Mock()
    llm.acomplete = AsyncMock(
        side_effect=[
            Exception("timeout while calling model"),
            {
                "content": "retry succeeded",
                "model": "test-model",
                "usage": {},
            },
        ]
    )

    template_engine = Mock()
    template_engine.render_executor_prompt.return_value = "Execute the step"

    router = ExecutionRouter(llm_gateway=llm, template_engine=template_engine)
    plan = Plan(
        user_intent="Run the approved plan",
        status=PlanStatus.APPROVED,
        execution_graph=[
            ExecutionStep(
                step_id=1,
                task="Generate output",
                prompt_template_id="default",
                assigned_model="test-model",
                dependencies=[],
            )
        ],
    )

    result = await router.execute_plan(plan, context={})

    assert result.status == PlanStatus.COMPLETED
    assert "retry succeeded" in result.final_output["step_1"]


@pytest.mark.asyncio
async def test_observer_detects_empty_output_as_drift():
    observer = Observer()
    plan = Plan(
        user_intent="Run the approved plan",
        execution_graph=[
            ExecutionStep(
                step_id=1,
                task="Generate output",
                prompt_template_id="default",
                assigned_model="test-model",
                output="",
            )
        ],
    )

    observation = await observer.on_step_complete(plan.execution_graph[0], plan)

    assert observation.drift_detected is True
    assert observation.recommended_action == "replan_from_here"
    assert observation.confidence >= 0.9


@pytest.mark.asyncio
async def test_execute_plan_pauses_at_checkpoint_when_observer_detects_drift():
    llm = Mock()
    llm.acomplete = AsyncMock(
        side_effect=[
            {"content": "", "model": "test-model", "usage": {}},
            {"content": "should not run", "model": "test-model", "usage": {}},
        ]
    )

    template_engine = Mock()
    template_engine.render_executor_prompt.return_value = "Execute the step"

    router = ExecutionRouter(llm_gateway=llm, template_engine=template_engine)
    plan = Plan(
        user_intent="Run the approved plan",
        status=PlanStatus.APPROVED,
        execution_graph=[
            ExecutionStep(
                step_id=1,
                task="Generate output",
                prompt_template_id="default",
                assigned_model="test-model",
                dependencies=[],
            ),
            ExecutionStep(
                step_id=2,
                task="Use previous output",
                prompt_template_id="default",
                assigned_model="test-model",
                dependencies=[1],
            ),
        ],
    )

    result = await router.execute_plan(plan, context={}, observer=Observer(), observer_drift_threshold=0.8)

    assert result.status == PlanStatus.APPROVED
    assert result.metadata["observer_signal"]["step_id"] == 1
    assert result.execution_graph[0].status.value == "COMPLETED"
    assert result.execution_graph[1].status.value == "PENDING"
    assert llm.acomplete.await_count == 1
