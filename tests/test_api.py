import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


class TestAPI:
    @pytest.fixture
    def mock_orchestrator(self):
        with patch("src.planweaver.api.routes.get_orchestrator") as mock_get:
            orchestrator = Mock()
            orchestrator.start_session = Mock(return_value=Mock(
                session_id="test-123",
                status=Mock(value="brainstorming"),
                open_questions=[]
            ))
            orchestrator.get_session = Mock(return_value=Mock(
                session_id="test-123",
                status=Mock(value="brainstorming"),
                user_intent="test intent",
                locked_constraints={},
                open_questions=[],
                strawman_proposals=[],
                execution_graph=[]
            ))
            mock_get.return_value = orchestrator
            yield orchestrator

    @pytest.fixture
    def client(self, mock_orchestrator):
        with patch("src.planweaver.api.routes.get_orchestrator", return_value=mock_orchestrator):
            with patch("src.planweaver.api.main.init_db"):
                from src.planweaver.api.main import app
                return TestClient(app)

    def test_create_session_requires_user_intent(self):
        with patch("src.planweaver.api.routes.get_orchestrator") as mock_get:
            mock_orch = Mock()
            mock_get.return_value = mock_orch
            
            from src.planweaver.api.main import app
            client = TestClient(app)
            
            response = client.post("/api/v1/sessions", json={})
            assert response.status_code == 422

    def test_create_session_returns_session_id(self, mock_orchestrator):
        from src.planweaver.api.main import app
        client = TestClient(app)
        
        with patch("src.planweaver.api.routes.get_orchestrator", return_value=mock_orchestrator):
            response = client.post("/api/v1/sessions", json={
                "user_intent": "Create a web app"
            })
            
            assert response.status_code == 200
            assert "session_id" in response.json()

    def test_get_session_not_found(self):
        with patch("src.planweaver.api.routes.get_orchestrator") as mock_get:
            mock_orch = Mock()
            mock_orch.get_session.return_value = None
            mock_get.return_value = mock_orch
            
            from src.planweaver.api.main import app
            client = TestClient(app)
            
            response = client.get("/api/v1/sessions/nonexistent")
            assert response.status_code == 404

    def test_list_models_returns_models(self, mock_orchestrator):
        from src.planweaver.api.main import app
        client = TestClient(app)
        
        mock_orchestrator.llm.get_available_models.return_value = [
            {"id": "gemini-3-pro-preview", "name": "Gemini 3 Pro", "type": "planner"}
        ]
        
        with patch("src.planweaver.api.routes.get_orchestrator", return_value=mock_orchestrator):
            response = client.get("/api/v1/models")
            
            assert response.status_code == 200
            assert "models" in response.json()
            models = response.json()["models"]
            assert any("gemini" in m["id"].lower() for m in models)

    def test_list_scenarios_returns_scenarios(self, mock_orchestrator):
        from src.planweaver.api.main import app
        client = TestClient(app)
        
        mock_orchestrator.template_engine.list_scenarios.return_value = [
            {"name": "test_scenario", "description": "A test"}
        ]
        
        with patch("src.planweaver.api.routes.get_orchestrator", return_value=mock_orchestrator):
            response = client.get("/api/v1/scenarios")
            
            assert response.status_code == 200
            assert "scenarios" in response.json()


class TestAPIValidation:
    def test_sessions_endpoint_requires_user_intent(self):
        from src.planweaver.api.main import app
        client = TestClient(app)
        
        response = client.post("/api/v1/sessions", json={})
        assert response.status_code == 422

    def test_execute_requires_approved_plan(self):
        with patch("src.planweaver.api.routes.get_orchestrator") as mock_get:
            from src.planweaver.models.plan import PlanStatus
            
            mock_orch = Mock()
            mock_plan = Mock()
            mock_plan.status = PlanStatus.BRAINSTORMING
            mock_orch.get_session.return_value = mock_plan
            mock_get.return_value = mock_orch
            
            from src.planweaver.api.main import app
            client = TestClient(app)
            
            response = client.post("/api/v1/sessions/test-123/execute", json={})
            assert response.status_code == 400
