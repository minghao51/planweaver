import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient


class TestAPI:
    @pytest.fixture
    def mock_orchestrator(self):
        with patch("src.planweaver.api.routers.sessions.get_orchestrator") as mock_get:
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
        with patch("src.planweaver.api.routers.sessions.get_orchestrator", return_value=mock_orchestrator):
            with patch("src.planweaver.api.main.init_db"):
                from src.planweaver.api.main import app
                return TestClient(app)

    def test_create_session_requires_user_intent(self):
        with patch("src.planweaver.api.routers.sessions.get_orchestrator") as mock_get:
            mock_orch = Mock()
            mock_get.return_value = mock_orch
            
            from src.planweaver.api.main import app
            client = TestClient(app)
            
            response = client.post("/api/v1/sessions", json={})
            assert response.status_code == 422

    def test_create_session_returns_session_id(self, mock_orchestrator):
        from src.planweaver.api.main import app
        client = TestClient(app)
        
        with patch("src.planweaver.api.routers.sessions.get_orchestrator", return_value=mock_orchestrator):
            response = client.post("/api/v1/sessions", json={
                "user_intent": "Create a web app"
            })
            
            assert response.status_code == 200
            assert "session_id" in response.json()

    def test_get_session_not_found(self):
        with patch("src.planweaver.api.routers.sessions.get_orchestrator") as mock_get:
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
        
        with patch("src.planweaver.api.routers.metadata.get_orchestrator", return_value=mock_orchestrator):
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
        
        with patch("src.planweaver.api.routers.metadata.get_orchestrator", return_value=mock_orchestrator):
            response = client.get("/api/v1/scenarios")
            
            assert response.status_code == 200
            assert "scenarios" in response.json()

    def test_list_sessions_returns_history(self):
        from src.planweaver.api.main import app
        client = TestClient(app)

        sessions = {
            "sessions": [
                {
                    "session_id": "proj_abc123",
                    "status": "COMPLETED",
                    "user_intent": "Refactor CLI into API",
                    "scenario_name": None,
                    "created_at": "2026-02-25T10:00:00+00:00",
                    "updated_at": "2026-02-25T10:05:00+00:00",
                }
            ],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }

        with patch("src.planweaver.api.routers.sessions.get_orchestrator") as mock_get:
            mock_orch = Mock()
            mock_orch.list_sessions.return_value = sessions
            mock_get.return_value = mock_orch

            response = client.get("/api/v1/sessions")

            assert response.status_code == 200
            payload = response.json()
            assert "sessions" in payload
            assert payload["sessions"][0]["session_id"] == "proj_abc123"
            assert payload["total"] == 1
            assert payload["offset"] == 0


class TestAPIValidation:
    def test_sessions_endpoint_requires_user_intent(self):
        from src.planweaver.api.main import app
        client = TestClient(app)
        
        response = client.post("/api/v1/sessions", json={})
        assert response.status_code == 422

    def test_execute_requires_approved_plan(self):
        with patch("src.planweaver.api.routers.sessions.get_orchestrator") as mock_get:
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
