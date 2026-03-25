"""Unit tests for EnsembleService (Pattern 3)"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.planweaver.services.ensemble import EnsembleService
from src.planweaver.models.plan import NormalizedPlan, ExecutionStep, PlanSourceType


@pytest.fixture
def mock_llm_gateway():
    """Mock LLM gateway"""
    llm = MagicMock()
    return llm


@pytest.fixture
def mock_planner():
    """Mock planner"""
    planner = MagicMock()
    return planner


@pytest.fixture
def mock_evaluator():
    """Mock evaluator"""
    evaluator = MagicMock()
    return evaluator


@pytest.fixture
def mock_comparison_service():
    """Mock comparison service"""
    comparison = MagicMock()
    return comparison


@pytest.fixture
def mock_plan_normalizer():
    """Mock plan normalizer"""
    normalizer = MagicMock()
    return normalizer


@pytest.fixture
def ensemble_service(
    mock_llm_gateway,
    mock_planner,
    mock_evaluator,
    mock_comparison_service,
    mock_plan_normalizer,
):
    """Create ensemble service with mocked dependencies"""
    return EnsembleService(
        mock_llm_gateway,
        mock_planner,
        mock_evaluator,
        mock_comparison_service,
        mock_plan_normalizer,
    )


class TestEnsembleService:
    """Test EnsembleService class"""

    def test_init(self, ensemble_service):
        """Test ensemble service initialization"""
        assert ensemble_service.llm is not None
        assert ensemble_service.planner is not None
        assert ensemble_service.evaluator is not None
        assert ensemble_service.comparison is not None
        assert ensemble_service.normalizer is not None

    @pytest.mark.asyncio
    async def test_run_ensemble_with_no_candidates(self, ensemble_service):
        """Test ensemble when no candidates are generated"""
        ensemble_service.planner.decompose_into_steps = MagicMock(return_value=None)

        result = await ensemble_service.run_ensemble(
            user_intent="Build something",
            models=["test-model"],
            locked_constraints={},
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_run_ensemble_with_exceptions(self, ensemble_service):
        """Test ensemble when models raise exceptions"""
        ensemble_service.planner.decompose_into_steps = MagicMock(side_effect=Exception("LLM error"))

        result = await ensemble_service.run_ensemble(
            user_intent="Build something",
            models=["test-model"],
            locked_constraints={},
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_candidate_success(self, ensemble_service):
        """Test generating a candidate successfully"""
        steps = [
            ExecutionStep(
                step_id=1,
                task="Test task",
                prompt_template_id="default",
                assigned_model="test-model",
                dependencies=[],
            )
        ]
        ensemble_service.planner.decompose_into_steps = MagicMock(return_value=steps)

        candidate = await ensemble_service._generate_candidate(
            user_intent="Build something",
            locked_constraints={},
            scenario_name=None,
            model="test-model",
        )

        assert candidate is not None
        assert candidate.source_model == "test-model"
        assert len(candidate.execution_graph) == 1

    @pytest.mark.asyncio
    async def test_generate_candidate_non_list_return(self, ensemble_service):
        """Test generating candidate when planner doesn't return a list"""
        ensemble_service.planner.decompose_into_steps = MagicMock(return_value="not a list")

        candidate = await ensemble_service._generate_candidate(
            user_intent="Build something",
            locked_constraints={},
            scenario_name=None,
            model="test-model",
        )

        assert candidate is None

    @pytest.mark.asyncio
    async def test_generate_candidate_with_exception(self, ensemble_service):
        """Test generating candidate when planner raises exception"""
        ensemble_service.planner.decompose_into_steps = MagicMock(side_effect=Exception("LLM error"))

        candidate = await ensemble_service._generate_candidate(
            user_intent="Build something",
            locked_constraints={},
            scenario_name=None,
            model="test-model",
        )

        assert candidate is None


class TestEnsembleServiceIntegration:
    """Integration tests for EnsembleService"""

    @pytest.mark.asyncio
    async def test_run_ensemble_full_flow(self, ensemble_service):
        """Test full ensemble flow with mocked components"""
        # Mock planner to return steps
        steps = [
            ExecutionStep(
                step_id=1,
                task="Test task",
                prompt_template_id="default",
                assigned_model="test-model",
                dependencies=[],
            )
        ]
        ensemble_service.planner.decompose_into_steps = MagicMock(return_value=steps)

        # Mock normalizer
        normalized_plan = NormalizedPlan(
            id="test-plan-id",
            source_type=PlanSourceType.LLM_GENERATED,
            source_model="test-model",
            title="Test Plan",
            summary="Test summary",
            steps=[],
        )
        ensemble_service.normalizer.normalize_generated_plan = MagicMock(return_value=normalized_plan)

        # Mock evaluator
        ensemble_service.evaluator.evaluate_plan = MagicMock(return_value={})

        # Mock comparison
        from src.planweaver.models.plan import RankedPlanResult, DisagreementLevel

        ranked_result = RankedPlanResult(
            plan_id="test-plan-id",
            final_score=8.5,
            rank=1,
            confidence=0.9,
            disagreement_level=DisagreementLevel.LOW,
            recommendation_reason="Test reason",
        )
        ensemble_service.comparison.rank_plans = MagicMock(return_value=[ranked_result])

        result = await ensemble_service.run_ensemble(
            user_intent="Build something",
            models=["test-model"],
            locked_constraints={},
        )

        assert result is not None
        assert result.id == "test-plan-id"

    @pytest.mark.asyncio
    async def test_run_ensemble_default_models(self, ensemble_service):
        """Test ensemble uses default models when none provided"""
        ensemble_service.planner.decompose_into_steps = MagicMock(return_value=[])
        ensemble_service.normalizer.normalize_generated_plan = MagicMock(side_effect=Exception("Should not be called"))

        # Should use default models
        with patch.object(
            ensemble_service,
            "_generate_candidate",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_generate:
            await ensemble_service.run_ensemble(
                user_intent="Build something",
                models=None,
                locked_constraints={},
            )

            # Should be called with default models
            assert mock_generate.call_count == len(EnsembleService.DEFAULT_MODELS)
