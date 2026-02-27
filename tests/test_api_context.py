import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient


class TestAPIContext:
    @pytest.fixture
    def mock_orchestrator(self):
        with patch("src.planweaver.api.dependencies.get_orchestrator_factory") as mock_get_factory:
            orchestrator = Mock()

            mock_plan = Mock()
            mock_plan.session_id = "test-123"
            mock_plan.external_contexts = []
            mock_plan.user_intent = "test intent"

            orchestrator.get_session = Mock(return_value=mock_plan)
            orchestrator.add_external_context = Mock()

            mock_get_factory.return_value = orchestrator
            yield orchestrator

    @pytest.fixture
    def client(self, mock_orchestrator):
        with patch("src.planweaver.api.dependencies.get_orchestrator_factory", return_value=mock_orchestrator):
            with patch("src.planweaver.api.main.init_db"):
                from src.planweaver.api.main import app
                return TestClient(app)

    def test_add_github_context(self, client, mock_orchestrator):
        """Test GitHub context API endpoint"""
        mock_context = Mock()
        mock_context.id = "ctx-123"
        mock_context.source_type = "github"
        mock_context.source_url = "https://github.com/test/repo"

        with patch("src.planweaver.api.routers.context.get_context_service") as mock_get_cs:
            mock_cs = AsyncMock()
            mock_cs.add_github_context = AsyncMock(return_value=mock_context)
            mock_get_cs.return_value = mock_cs

            response = client.post(
                "/api/v1/sessions/test-123/context/github",
                json={"repo_url": "https://github.com/test/repo"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["source_type"] == "github"
            assert "context_id" in data

    def test_list_contexts(self, client, mock_orchestrator):
        """Test listing contexts for a session"""
        from src.planweaver.models.plan import ExternalContext
        from datetime import datetime, timezone

        context = ExternalContext(
            id="ctx-1",
            source_type="github",
            source_url="https://github.com/test/repo",
            content_summary="Test repo",
            metadata={},
            created_at=datetime.now(timezone.utc)
        )
        mock_plan = mock_orchestrator.get_session.return_value
        mock_plan.external_contexts = [context]

        response = client.get("/api/v1/sessions/test-123/context")

        assert response.status_code == 200
        data = response.json()
        assert len(data["contexts"]) == 1
        assert data["contexts"][0]["source_type"] == "github"

    def test_add_web_search_context(self, client, mock_orchestrator):
        """Test web search API endpoint"""
        mock_context = Mock()
        mock_context.id = "ctx-456"
        mock_context.source_type = "web_search"

        with patch("src.planweaver.api.routers.context.get_context_service") as mock_get_cs:
            mock_cs = AsyncMock()
            mock_cs.add_web_search_context = AsyncMock(return_value=mock_context)
            mock_get_cs.return_value = mock_cs

            response = client.post(
                "/api/v1/sessions/test-123/context/web-search",
                json={"query": "FastAPI best practices"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["source_type"] == "web_search"

    def test_upload_file_context(self, client, mock_orchestrator):
        """Test file upload API endpoint"""
        mock_context = Mock()
        mock_context.id = "ctx-789"
        mock_context.source_type = "file_upload"

        with patch("src.planweaver.api.routers.context.get_context_service") as mock_get_cs:
            mock_cs = AsyncMock()
            mock_cs.add_file_context = AsyncMock(return_value=mock_context)
            mock_get_cs.return_value = mock_cs

            response = client.post(
                "/api/v1/sessions/test-123/context/upload",
                files={"file": ("test.txt", b"test content", "text/plain")}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["source_type"] == "file_upload"

    def test_context_not_found_session(self, client, mock_orchestrator):
        """Test context endpoints with non-existent session"""
        mock_orchestrator.get_session.return_value = None

        response = client.get("/api/v1/sessions/nonexistent/context")

        assert response.status_code == 404
