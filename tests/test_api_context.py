import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient


class TestAPIContext:
    @pytest.fixture
    def mock_orchestrator(self):
        with patch("src.planweaver.api.routes.get_orchestrator") as mock_get:
            orchestrator = Mock()

            # Mock plan
            mock_plan = Mock()
            mock_plan.session_id = "test-123"
            mock_plan.external_contexts = []

            orchestrator.get_session = Mock(return_value=mock_plan)
            orchestrator.add_external_context = Mock(return_value=mock_plan)

            mock_get.return_value = orchestrator
            yield orchestrator

    @pytest.fixture
    def client(self, mock_orchestrator):
        with patch("src.planweaver.api.routes.get_orchestrator", return_value=mock_orchestrator):
            with patch("src.planweaver.api.main.init_db"):
                from src.planweaver.api.main import app
                return TestClient(app)

    def test_add_github_context(self, client, mock_orchestrator, mocker):
        """Test GitHub context API endpoint"""
        # Mock context service
        mock_context = Mock()
        mock_context.id = "ctx-123"
        mock_context.source_type = "github"
        mock_context.source_url = "https://github.com/test/repo"

        mock_add_github = mocker.patch(
            "src.planweaver.services.context_service.ContextService.add_github_context",
            new=mocker.AsyncMock(return_value=mock_context)
        )

        mocker.patch(
            "src.planweaver.api.routes.get_context_service",
            return_value=Mock(add_github_context=mock_add_github)
        )

        # Add context
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

        # Add a context to the mock plan
        context = ExternalContext(
            source_type="github",
            content_summary="Test"
        )
        mock_plan = mock_orchestrator.get_session.return_value
        mock_plan.external_contexts = [context]

        # List contexts
        response = client.get("/api/v1/sessions/test-123/context")

        assert response.status_code == 200
        data = response.json()
        assert len(data["contexts"]) == 1
        assert data["contexts"][0]["source_type"] == "github"

    def test_add_web_search_context(self, client, mock_orchestrator, mocker):
        """Test web search API endpoint"""
        mock_context = Mock()
        mock_context.id = "ctx-456"
        mock_context.source_type = "web_search"
        mock_context.metadata = {"query": "FastAPI best practices"}

        mock_add_search = mocker.patch(
            "src.planweaver.services.context_service.ContextService.add_web_search_context",
            new=mocker.AsyncMock(return_value=mock_context)
        )

        mocker.patch(
            "src.planweaver.api.routes.get_context_service",
            return_value=Mock(add_web_search_context=mock_add_search)
        )

        response = client.post(
            "/api/v1/sessions/test-123/context/web-search",
            json={"query": "FastAPI best practices"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "web_search"
        assert data["query"] == "FastAPI best practices"

    def test_upload_file_context(self, client, mock_orchestrator, mocker):
        """Test file upload API endpoint"""
        mock_context = Mock()
        mock_context.id = "ctx-789"
        mock_context.source_type = "file_upload"
        mock_context.metadata = {"filename": "test.txt"}

        mock_add_file = mocker.patch(
            "src.planweaver.services.context_service.ContextService.add_file_context",
            new=mocker.AsyncMock(return_value=mock_context)
        )

        mocker.patch(
            "src.planweaver.api.routes.get_context_service",
            return_value=Mock(add_file_context=mock_add_file)
        )

        response = client.post(
            "/api/v1/sessions/test-123/context/upload",
            files={"file": ("test.txt", b"test content", "text/plain")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "file_upload"
        assert data["filename"] == "test.txt"

    def test_context_not_found_session(self, client, mock_orchestrator):
        """Test context endpoints with non-existent session"""
        mock_orchestrator.get_session.return_value = None

        response = client.get("/api/v1/sessions/nonexistent/context")

        assert response.status_code == 404
