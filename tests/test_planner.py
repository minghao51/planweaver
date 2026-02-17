import pytest
from unittest.mock import Mock, patch


class TestPlanner:
    @pytest.fixture
    def mock_llm_gateway(self):
        gateway = Mock()
        gateway.complete = Mock(return_value={
            "content": '{"identified_constraints": ["Python"], "missing_information": [], "suggested_approach": "test", "estimated_complexity": "low"}',
            "model": "test",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        })
        return gateway

    def test_analyze_intent_returns_analysis(self, mock_llm_gateway):
        with patch("src.planweaver.services.planner.LLMGateway", return_value=mock_llm_gateway):
            from src.planweaver.services.planner import Planner
            planner = Planner(llm_gateway=mock_llm_gateway)
            
            result = planner.analyze_intent("Create a Python web app")
            
            assert "identified_constraints" in result
            assert "missing_information" in result
            assert "suggested_approach" in result
            assert "estimated_complexity" in result

    def test_analyze_intent_handles_json_error(self):
        mock_gateway = Mock()
        mock_gateway.complete = Mock(return_value={
            "content": "not valid json",
            "model": "test",
            "usage": {}
        })
        
        from src.planweaver.services.planner import Planner
        planner = Planner(llm_gateway=mock_gateway)
        
        result = planner.analyze_intent("test request")
        
        assert "identified_constraints" in result
        assert result["estimated_complexity"] == "unknown"

    def test_create_initial_plan_returns_plan(self, mock_llm_gateway):
        with patch("src.planweaver.services.planner.LLMGateway", return_value=mock_llm_gateway):
            from src.planweaver.services.planner import Planner
            from src.planweaver.models.plan import PlanStatus
            
            planner = Planner(llm_gateway=mock_llm_gateway)
            plan = planner.create_initial_plan("Create a web app")
            
            assert plan.user_intent == "Create a web app"
            assert plan.status == PlanStatus.BRAINSTORMING
            assert plan.session_id is not None

    @pytest.fixture
    def mock_planner_llm_for_decompose(self):
        gateway = Mock()
        gateway.complete = Mock(return_value={
            "content": '[{"step_id": 1, "task": "Setup project", "prompt_template_id": "setup", "assigned_model": "claude", "dependencies": []}]',
            "model": "test",
            "usage": {}
        })
        return gateway

    def test_decompose_into_steps_returns_steps(self, mock_planner_llm_for_decompose):
        from src.planweaver.services.planner import Planner
        from src.planweaver.models.plan import ExecutionStep, StepStatus
        
        planner = Planner(llm_gateway=mock_planner_llm_for_decompose)
        steps = planner.decompose_into_steps(
            user_intent="Create web app",
            locked_constraints={}
        )
        
        assert len(steps) > 0
        assert isinstance(steps[0], ExecutionStep)
        assert steps[0].status == StepStatus.PENDING

    def test_decompose_handles_json_error(self):
        mock_gateway = Mock()
        mock_gateway.complete = Mock(return_value={
            "content": "invalid",
            "model": "test",
            "usage": {}
        })
        
        from src.planweaver.services.planner import Planner
        planner = Planner(llm_gateway=mock_gateway)
        
        steps = planner.decompose_into_steps("test", {})
        
        assert len(steps) == 1
        assert steps[0].task == "Execute user request directly"

    @pytest.fixture
    def mock_gateway_for_proposals(self):
        gateway = Mock()
        gateway.complete = Mock(return_value={
            "content": '[{"title": "Approach 1", "description": "Desc", "pros": ["Pro 1"], "cons": ["Con 1"]}]',
            "model": "test",
            "usage": {}
        })
        return gateway

    def test_generate_strawman_proposals(self, mock_gateway_for_proposals):
        from src.planweaver.services.planner import Planner
        planner = Planner(llm_gateway=mock_gateway_for_proposals)
        
        proposals = planner.generate_strawman_proposals("Create app")
        
        assert len(proposals) > 0
        assert proposals[0].title == "Approach 1"

    def test_generate_strawman_handles_json_error(self):
        mock_gateway = Mock()
        mock_gateway.complete = Mock(return_value={
            "content": "invalid",
            "model": "test",
            "usage": {}
        })
        
        from src.planweaver.services.planner import Planner
        planner = Planner(llm_gateway=mock_gateway)
        
        proposals = planner.generate_strawman_proposals("test")
        
        assert proposals == []
