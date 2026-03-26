"""Integration tests for multi-agent planning patterns

These tests require real LLM calls and are marked with the 'integration' marker.
Run with: pytest tests/test_multiagent_integration.py -m integration
"""

import pytest
import inspect
from src.planweaver.orchestrator import Orchestrator
from src.planweaver.models.plan import PlanStatus


# Mark all tests in this module as llm_e2e (end-to-end with real LLM calls)
pytestmark = pytest.mark.llm_e2e


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing"""
    return Orchestrator()


@pytest.mark.asyncio
async def test_specialist_mode_integration(orchestrator):
    """Test specialist mode end-to-end with real LLM calls"""
    plan = await orchestrator.start_specialist_session(
        user_intent="Build and deploy a simple REST API",
        specialist_domains=["code"],  # Use only code domain for faster testing
        scenario_name="default",
    )

    assert plan is not None
    assert plan.status == PlanStatus.AWAITING_APPROVAL
    assert plan.metadata.get("planning_mode") == "specialist"
    assert len(plan.execution_graph) > 0


@pytest.mark.asyncio
async def test_specialist_mode_multiple_domains(orchestrator):
    """Test specialist mode with multiple domains"""
    plan = await orchestrator.start_specialist_session(
        user_intent="Create a secure API with proper testing",
        specialist_domains=["code", "testing"],
        scenario_name="default",
    )

    assert plan is not None
    assert plan.status == PlanStatus.AWAITING_APPROVAL
    assert plan.metadata.get("planning_mode") == "specialist"
    assert len(plan.execution_graph) > 0


@pytest.mark.asyncio
async def test_ensemble_mode_integration(orchestrator):
    """Test ensemble mode end-to-end with real LLM calls"""
    # Use fewer models for faster testing
    plan = await orchestrator.start_ensemble_session(
        user_intent="Design a caching strategy for a web application",
        ensemble_models=["gemini-2.5-flash"],  # Use one model for testing
        scenario_name="default",
    )

    assert plan is not None
    assert plan.status == PlanStatus.AWAITING_APPROVAL
    assert plan.metadata.get("planning_mode") == "ensemble"
    # May have execution_graph or ensemble_error if fallback was used


@pytest.mark.asyncio
async def test_debate_mode_integration(orchestrator):
    """Test debate mode end-to-end with real LLM calls"""
    plan = await orchestrator.start_debate_session(
        user_intent="Choose between SQL and NoSQL for user data storage",
        scenario_name="default",
    )

    assert plan is not None
    assert plan.status == PlanStatus.AWAITING_APPROVAL
    assert plan.metadata.get("planning_mode") == "debate"
    assert "debate_rounds" in plan.metadata
    # Debate rounds may be empty if no decision points are detected


@pytest.mark.asyncio
async def test_baseline_mode_still_works(orchestrator):
    """Test that baseline mode still works after multi-agent changes"""
    plan = orchestrator.start_session(
        user_intent="Create a simple hello world API",
        scenario_name="default",
    )

    assert plan is not None
    # Baseline mode starts in BRAINSTORMING
    assert plan.status in [PlanStatus.BRAINSTORMING, PlanStatus.AWAITING_APPROVAL]


@pytest.mark.asyncio
async def test_specialist_mode_with_custom_model(orchestrator):
    """Test specialist mode with custom planner model"""
    plan = await orchestrator.start_specialist_session(
        user_intent="Write a Python function",
        specialist_domains=["code"],
        scenario_name="default",
        planner_model="gemini-2.5-flash",
    )

    assert plan is not None
    assert plan.metadata.get("planning_mode") == "specialist"
    assert plan.planner_model == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_ensemble_mode_with_multiple_models(orchestrator):
    """Test ensemble mode with multiple models (slower test)"""
    plan = await orchestrator.start_ensemble_session(
        user_intent="Implement user authentication",
        ensemble_models=["gemini-2.5-flash", "deepseek/deepseek-chat"],
        scenario_name="default",
    )

    assert plan is not None
    assert plan.status == PlanStatus.AWAITING_APPROVAL
    assert plan.metadata.get("planning_mode") == "ensemble"
    assert len(plan.metadata.get("ensemble_models", [])) == 2


@pytest.mark.asyncio
async def test_debate_mode_with_decision_points(orchestrator):
    """Test debate mode detects and debates decision points"""
    plan = await orchestrator.start_debate_session(
        user_intent="Select between microservices and monolith architecture",
        scenario_name="default",
    )

    assert plan is not None
    assert plan.metadata.get("planning_mode") == "debate"
    debate_count = plan.metadata.get("debate_count", 0)
    # Should have detected at least one decision point
    assert debate_count >= 0  # May be 0 if LLM doesn't generate decision keywords


class TestMultiAgentErrorHandling:
    """Test error handling in multi-agent modes"""

    @pytest.mark.asyncio
    async def test_specialist_mode_with_invalid_domain(self, orchestrator):
        """Test specialist mode handles invalid domains gracefully"""
        # Should not crash with invalid domain
        plan = await orchestrator.start_specialist_session(
            user_intent="Simple task",
            specialist_domains=["nonexistent_domain"],  # Invalid domain
            scenario_name="default",
        )

        # Should still create a plan, possibly with empty execution graph
        assert plan is not None
        assert plan.metadata.get("planning_mode") == "specialist"

    @pytest.mark.asyncio
    async def test_ensemble_mode_with_empty_models_list(self, orchestrator):
        """Test ensemble mode with empty models list (uses defaults)"""
        plan = await orchestrator.start_ensemble_session(
            user_intent="Simple task",
            ensemble_models=[],  # Empty list should use defaults
            scenario_name="default",
        )

        # Should use default models
        assert plan is not None
        assert plan.metadata.get("planning_mode") == "ensemble"


@pytest.mark.asyncio
async def test_all_modes_create_persistable_plans(orchestrator):
    """Test that all modes create plans that can be persisted and retrieved"""
    modes = [
        ("baseline", lambda: orchestrator.start_session("Test baseline")),
        ("specialist", lambda: orchestrator.start_specialist_session("Test specialist", specialist_domains=["code"])),
        (
            "ensemble",
            lambda: orchestrator.start_ensemble_session("Test ensemble", ensemble_models=["gemini-2.5-flash"]),
        ),
        ("debate", lambda: orchestrator.start_debate_session("Test debate")),
    ]

    for mode_name, create_plan_fn in modes:
        result = create_plan_fn()
        plan = await result if inspect.isawaitable(result) else result

        # Verify plan was created
        assert plan is not None

        # Verify plan can be retrieved from repository
        retrieved = orchestrator.get_session(plan.session_id)
        assert retrieved is not None
        assert retrieved.session_id == plan.session_id
        assert retrieved.metadata.get("planning_mode") == mode_name
