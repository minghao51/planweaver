"""Unit tests for DebateService (Pattern 7)"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from src.planweaver.services.debate import DebateService
from src.planweaver.models.coordination import DebateRound
from src.planweaver.models.plan import Plan, ExecutionStep


@pytest.fixture
def mock_llm_gateway():
    """Mock LLM gateway"""
    llm = MagicMock()
    return llm


@pytest.fixture
def debate_service(mock_llm_gateway):
    """Create debate service with mocked LLM gateway"""
    return DebateService(mock_llm_gateway)


@pytest.fixture
def sample_plan():
    """Create a sample plan for testing"""
    plan = Plan(
        user_intent="Build a REST API",
        scenario_name="default",
    )
    plan.execution_graph = [
        ExecutionStep(
            step_id=1,
            task="Choose between SQL and NoSQL database",
            prompt_template_id="default",
            assigned_model="test",
            dependencies=[],
        ),
        ExecutionStep(
            step_id=2,
            task="Implement API endpoints",
            prompt_template_id="default",
            assigned_model="test",
            dependencies=[],
        ),
        ExecutionStep(
            step_id=3,
            task="Evaluate caching strategy options",
            prompt_template_id="default",
            assigned_model="test",
            dependencies=[],
        ),
    ]
    return plan


class TestDebateService:
    """Test DebateService class"""

    def test_init(self, debate_service):
        """Test debate service initialization"""
        assert debate_service.llm is not None

    def test_detect_decision_points(self, debate_service, sample_plan):
        """Test detecting decision points in execution graph"""
        decision_points = debate_service.detect_decision_points(sample_plan)

        # Should detect steps with decision keywords
        assert len(decision_points) >= 2
        assert any("Choose between" in dp for dp in decision_points)
        assert any("Evaluate" in dp for dp in decision_points)

    def test_detect_decision_points_empty_plan(self, debate_service):
        """Test detecting decision points in plan with no execution graph"""
        plan = Plan(user_intent="Test", scenario_name="default")
        plan.execution_graph = []

        decision_points = debate_service.detect_decision_points(plan)
        assert decision_points == []

    def test_detect_decision_points_no_keywords(self, debate_service):
        """Test detecting decision points when no keywords match"""
        plan = Plan(user_intent="Test", scenario_name="default")
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="Implement feature",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[],
            )
        ]

        decision_points = debate_service.detect_decision_points(plan)
        assert decision_points == []

    @pytest.mark.asyncio
    async def test_conduct_debate_round(self, debate_service, sample_plan):
        """Test conducting a single debate round"""
        decision_point = "Choose between SQL and NoSQL database"

        # Mock LLM responses
        debate_service.llm.acomplete = AsyncMock(
            side_effect=[
                {"content": "I support using SQL because it provides ACID compliance and structured schema."},
                {"content": "I oppose using SQL because NoSQL offers better scalability and flexibility."},
                {
                    "content": "Selected: proposer\nRationale: The project requires strong consistency and SQL provides the necessary transaction support."
                },
            ]
        )

        result = await debate_service.conduct_debate_round(
            decision_point=decision_point,
            plan=sample_plan,
        )

        assert isinstance(result, DebateRound)
        assert result.decision_point == decision_point
        assert len(result.proposer_argument) > 0
        assert len(result.opposer_argument) > 0
        assert len(result.synthesizer_decision) > 0
        assert result.selected_approach in ["proposer", "opposer"]

    def test_parse_selected_approach_proposer(self, debate_service):
        """Test parsing selected approach for proposer"""
        synthesis = "After reviewing both arguments, Selected: proposer because the benefits outweigh the risks."
        result = debate_service._parse_selected_approach(synthesis)
        assert result == "proposer"

    def test_parse_selected_approach_opposer(self, debate_service):
        """Test parsing selected approach for opposer"""
        synthesis = "The risks identified are significant. Selected: opposer to avoid potential failures."
        result = debate_service._parse_selected_approach(synthesis)
        assert result == "opposer"

    def test_parse_selected_approach_keyword_fallback(self, debate_service):
        """Test parsing selected approach using keyword fallback"""
        synthesis = "I support the proposer's argument and agree with their assessment."
        result = debate_service._parse_selected_approach(synthesis)
        assert result == "proposer"

    def test_parse_selected_approach_default(self, debate_service):
        """Test parsing selected approach defaults to proposer when unclear"""
        synthesis = "Both arguments have merit but the decision is unclear."
        result = debate_service._parse_selected_approach(synthesis)
        assert result == "proposer"  # Default


class TestDebateServiceIntegration:
    """Integration tests for DebateService"""

    @pytest.mark.asyncio
    async def test_conduct_multiple_debate_rounds(self, debate_service, sample_plan):
        """Test conducting multiple debate rounds"""
        decision_points = debate_service.detect_decision_points(sample_plan)

        # Mock LLM responses
        debate_service.llm.acomplete = AsyncMock(
            side_effect=[
                {"content": "Proponent argument"},
                {"content": "Opponent argument"},
                {"content": "Selected: proposer\nRationale: Test reasoning"},
            ]
            * len(decision_points)
        )

        debate_rounds = []
        for dp in decision_points[:2]:  # Limit to 2 for testing
            result = await debate_service.conduct_debate_round(dp, sample_plan)
            debate_rounds.append(result)

        assert len(debate_rounds) == 2
        assert all(isinstance(dr, DebateRound) for dr in debate_rounds)

    @pytest.mark.asyncio
    async def test_conduct_debate_round_custom_models(self, debate_service, sample_plan):
        """Test conducting debate with custom models"""
        decision_point = "Test decision"

        debate_service.llm.acomplete = AsyncMock(
            side_effect=[
                {"content": "Proponent"},
                {"content": "Opponent"},
                {"content": "Selected: proposer\nRationale: Test"},
            ]
        )

        await debate_service.conduct_debate_round(
            decision_point=decision_point,
            plan=sample_plan,
            proposer_model="custom-proposer",
            opposer_model="custom-opposer",
            synthesizer_model="custom-synthesizer",
        )

        # Verify correct models were used
        calls = debate_service.llm.acomplete.call_args_list
        assert calls[0][1]["model"] == "custom-proposer"
        assert calls[1][1]["model"] == "custom-opposer"
        assert calls[2][1]["model"] == "custom-synthesizer"

    @pytest.mark.asyncio
    async def test_conduct_debate_round_uses_defaults(self, debate_service, sample_plan):
        """Test conducting debate uses default models when not specified"""
        decision_point = "Test decision"

        debate_service.llm.acomplete = AsyncMock(
            side_effect=[
                {"content": "Proponent"},
                {"content": "Opponent"},
                {"content": "Selected: proposer\nRationale: Test"},
            ]
        )

        await debate_service.conduct_debate_round(
            decision_point=decision_point,
            plan=sample_plan,
        )

        # Verify default models were used
        calls = debate_service.llm.acomplete.call_args_list
        assert calls[0][1]["model"] == "claude-3.5-sonnet"
        assert calls[1][1]["model"] == "gpt-4o"
        assert calls[2][1]["model"] == "deepseek-chat"
