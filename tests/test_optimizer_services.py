"""Tests for optimizer services"""
import pytest
from unittest.mock import Mock, patch
from planweaver.services.variant_generator import VariantGenerator
from planweaver.services.model_rater import ModelRater
from planweaver.services.optimizer_service import OptimizerService


class TestVariantGenerator:
    """Test VariantGenerator service"""

    def test_init(self):
        """Test VariantGenerator initialization"""
        generator = VariantGenerator()
        assert generator.llm_gateway is not None

    @patch('planweaver.services.variant_generator.LLMGateway')
    def test_get_system_prompt_simplified(self, mock_llm):
        """Test simplified variant system prompt"""
        generator = VariantGenerator()
        prompt = generator._get_system_prompt("simplified")
        assert "SIMPLIFIED" in prompt
        assert "Reduces the number of steps" in prompt

    @patch('planweaver.services.variant_generator.LLMGateway')
    def test_get_system_prompt_enhanced(self, mock_llm):
        """Test enhanced variant system prompt"""
        generator = VariantGenerator()
        prompt = generator._get_system_prompt("enhanced")
        assert "ENHANCED" in prompt
        assert "error handling" in prompt

    @patch('planweaver.services.variant_generator.LLMGateway')
    def test_get_system_prompt_cost_optimized(self, mock_llm):
        """Test cost-optimized variant system prompt"""
        generator = VariantGenerator()
        prompt = generator._get_system_prompt("cost-optimized")
        assert "COST-OPTIMIZED" in prompt
        assert "cheaper models" in prompt


class TestModelRater:
    """Test ModelRater service"""

    def test_init(self):
        """Test ModelRater initialization"""
        rater = ModelRater()
        assert rater.llm_gateway is not None
        assert rater.DEFAULT_MODELS == ["claude-3.5-sonnet", "gpt-4o", "deepseek-chat"]

    def test_criteria_defined(self):
        """Test rating criteria are defined"""
        rater = ModelRater()
        assert "feasibility" in rater.CRITERIA
        assert "cost_efficiency" in rater.CRITERIA
        assert "time_efficiency" in rater.CRITERIA

    @patch('planweaver.services.model_rater.LLMGateway')
    def test_get_error_rating(self, mock_llm):
        """Test error rating generation"""
        rater = ModelRater()
        error_rating = rater._get_error_rating("Test error")
        assert error_rating["model_name"] == "error"
        assert error_rating["overall_score"] == 5.0
        assert "Test error" in error_rating["reasoning"]


class TestOptimizerService:
    """Test OptimizerService"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()

    @patch('planweaver.services.optimizer_service.VariantGenerator')
    @patch('planweaver.services.optimizer_service.ModelRater')
    @patch('planweaver.services.optimizer_service.PlanRepository')
    def test_init(self, mock_repo, mock_rater, mock_gen, mock_db):
        """Test OptimizerService initialization"""
        service = OptimizerService(mock_db)
        assert service.db == mock_db
        assert service.variant_generator is not None
        assert service.model_rater is not None
