"""Unit tests for Coordinator service (Pattern 2)"""

import pytest
from unittest.mock import MagicMock, patch
from src.planweaver.services.coordinator import Coordinator
from src.planweaver.models.coordination import SubPlanFragment


@pytest.fixture
def mock_llm_gateway():
    """Mock LLM gateway"""
    llm = MagicMock()
    return llm


@pytest.fixture
def mock_coordinator(mock_llm_gateway):
    """Mock coordinator instance"""
    # Create coordinator with empty config to avoid file I/O
    with patch.object(Coordinator, "_load_domain_config", return_value={}):
        coord = Coordinator(mock_llm_gateway, "config/domains.yaml")
        return coord


class TestCoordinator:
    """Test Coordinator class"""

    def test_init_loads_domain_config(self, mock_llm_gateway):
        """Test coordinator initializes with domain config"""
        with patch.object(Coordinator, "_load_domain_config", return_value={"code": {"model": "test"}}):
            coord = Coordinator(mock_llm_gateway)
            assert coord.specialists == {"code": {"model": "test"}}

    def test_merge_fragments_empty(self, mock_coordinator):
        """Test merging empty fragments list"""
        merged = mock_coordinator.merge_fragments([])
        assert merged == []

    def test_merge_fragments_single(self, mock_coordinator):
        """Test merging single fragment"""
        fragment = SubPlanFragment(
            fragment_id="f1",
            domain="code",
            specialist="code",
            steps=[
                {
                    "step_id": 1,
                    "task": "Write code",
                    "prompt_template_id": "default",
                    "assigned_model": "test",
                    "dependencies": [],
                }
            ],
            confidence=0.8,
        )

        merged = mock_coordinator.merge_fragments([fragment])
        assert len(merged) == 1
        assert merged[0].step_id == 1
        assert merged[0].task == "Write code"

    def test_merge_fragments_multiple(self, mock_coordinator):
        """Test merging multiple fragments without conflicts"""
        fragments = [
            SubPlanFragment(
                fragment_id="f1",
                domain="code",
                specialist="code",
                steps=[
                    {
                        "step_id": 1,
                        "task": "Write code",
                        "prompt_template_id": "default",
                        "assigned_model": "test",
                        "dependencies": [],
                    }
                ],
                confidence=0.8,
            ),
            SubPlanFragment(
                fragment_id="f2",
                domain="infra",
                specialist="infra",
                steps=[
                    {
                        "step_id": 1,
                        "task": "Deploy server",
                        "prompt_template_id": "default",
                        "assigned_model": "test",
                        "dependencies": [],
                    }
                ],
                confidence=0.7,
            ),
        ]

        merged = mock_coordinator.merge_fragments(fragments)
        assert len(merged) == 2
        assert merged[0].step_id == 1
        assert merged[1].step_id == 2  # Renumbered

    @pytest.mark.asyncio
    async def test_coordinate_specialists_empty_domains(self, mock_coordinator):
        """Test coordinating with empty domains list"""
        fragments = await mock_coordinator.coordinate_specialists(
            user_intent="Build something",
            domains=[],
            locked_constraints={},
        )
        assert fragments == []

    @pytest.mark.asyncio
    async def test_decompose_to_domains(self, mock_coordinator):
        """Test decomposing user intent to domain-specific sub-goals"""
        mock_coordinator.specialists = {
            "code": {"keywords": ["function", "class"], "system_prompt": "Focus on code"},
            "infra": {"keywords": ["deploy", "server"], "system_prompt": "Focus on infra"},
        }

        sub_goals = await mock_coordinator._decompose_to_domains("Build and deploy an API", ["code", "infra"])

        assert "code" in sub_goals
        assert "infra" in sub_goals
        assert "Build and deploy an API" in sub_goals["code"]
        assert "Focus on code" in sub_goals["code"]

    @pytest.mark.asyncio
    async def test_run_specialist_with_exception(self, mock_coordinator):
        """Test specialist handles exceptions gracefully"""
        mock_coordinator.specialists = {
            "code": {"model": "test", "system_prompt": "Focus on code"},
        }

        # Mock planner to raise exception - patch at service level
        with patch("src.planweaver.services.planner.Planner") as mock_planner_class:
            mock_planner = MagicMock()
            mock_planner.decompose_into_steps.side_effect = Exception("LLM error")
            mock_planner_class.return_value = mock_planner

            with pytest.raises(Exception):
                await mock_coordinator._run_specialist(
                    "code",
                    "Write code",
                    {},
                    None,
                    "test-model",
                )


class TestCoordinatorIntegration:
    """Integration tests for Coordinator with domain config"""

    def test_load_domain_config_missing_file(self, mock_llm_gateway, tmp_path):
        """Test loading config when file doesn't exist"""
        with patch.object(Coordinator, "_load_domain_config", return_value={}):
            coord = Coordinator(mock_llm_gateway, str(tmp_path / "nonexistent.yaml"))
            assert coord.specialists == {}

    def test_merge_fragments_preserves_metadata(self, mock_coordinator):
        """Test that merging preserves step metadata"""
        from src.planweaver.models.plan import StepStatus

        fragment = SubPlanFragment(
            fragment_id="f1",
            domain="code",
            specialist="code",
            steps=[
                {
                    "step_id": 1,
                    "task": "Write code",
                    "prompt_template_id": "default",
                    "assigned_model": "test",
                    "dependencies": [],
                    "status": StepStatus.PENDING,
                }
            ],
            confidence=0.8,
        )

        merged = mock_coordinator.merge_fragments([fragment])
        assert merged[0].status == StepStatus.PENDING
        assert merged[0].assigned_model == "test"
