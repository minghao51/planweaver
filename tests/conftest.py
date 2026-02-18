import pytest
from unittest.mock import Mock, patch
from planweaver.config import Settings
from planweaver.services.llm_gateway import LLMGateway


@pytest.fixture
def mock_llm_response():
    def _mock_response(content: str, json_mode: bool = False):
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message.content = content
        response.usage = Mock()
        response.usage.dict.return_value = {"prompt_tokens": 100, "completion_tokens": 50}
        return response
    return _mock_response


@pytest.fixture
def settings():
    """Test settings fixture"""
    return Settings()


@pytest.fixture
def llm_gateway():
    """Test LLM gateway fixture"""
    return LLMGateway()


@pytest.fixture
def mock_llm_gateway(mock_llm_response):
    with patch("src.planweaver.services.llm_gateway.completion") as mock_complete:
        with patch("src.planweaver.services.llm_gateway.acompletion") as mock_acomplete:
            mock_complete.return_value = mock_llm_response("test response")
            mock_acomplete.return_value = mock_llm_response("test response")
            
            from src.planweaver.services.llm_gateway import LLMGateway
            gateway = LLMGateway()
            gateway._complete = mock_complete
            gateway._acomplete = mock_acomplete
            yield gateway


@pytest.fixture
def sample_plan_data():
    return {
        "session_id": "test-session-123",
        "user_intent": "Create a web app",
        "scenario_name": "code_refactoring",
        "status": "brainstorming",
        "locked_constraints": {},
        "open_questions": [
            {"id": "q1", "question": "What framework?", "answer": None, "answered": False}
        ],
        "strawman_proposals": [],
        "execution_graph": []
    }


@pytest.fixture
def sample_execution_step():
    return {
        "step_id": 1,
        "task": "Create project structure",
        "prompt_template_id": "create_dirs",
        "assigned_model": "claude-3-5-sonnet",
        "dependencies": [],
        "status": "pending"
    }
