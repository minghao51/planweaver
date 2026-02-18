"""End-to-end integration tests for external context features"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from planweaver.models.plan import ExternalContext, Plan, PlanStatus
from planweaver.orchestrator import Orchestrator


class TestE2EContextWorkflow:
    """Test complete workflows with external context"""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create orchestrator with mocked planner for testing"""
        with patch("planweaver.orchestrator.Planner") as mock_planner_class:
            # Create mock planner
            mock_planner = Mock()
            mock_planner.create_initial_plan.return_value = Plan(
                session_id="e2e-test-123",
                status=PlanStatus.BRAINSTORMING,
                user_intent="Refactor this codebase"
            )
            mock_planner_class.return_value = mock_planner

            # Create orchestrator
            orchestrator = Orchestrator()
            yield orchestrator

    def test_complete_github_workflow(self, mock_orchestrator, mocker):
        """Test complete workflow: GitHub context -> planning -> execution"""
        # 1. Start session
        plan = mock_orchestrator.start_session("Refactor this codebase to TypeScript")
        assert plan.status == PlanStatus.BRAINSTORMING
        assert plan.session_id == "e2e-test-123"

        # 2. Add GitHub context
        github_context = ExternalContext(
            source_type="github",
            source_url="https://github.com/user/javascript-app",
            content_summary="## GitHub Repo: javascript-app\nLanguage: JavaScript\nStars: 150"
        )

        plan = mock_orchestrator.add_external_context(plan.session_id, github_context)

        # 3. Verify context was added
        assert len(plan.external_contexts) == 1
        assert plan.external_contexts[0].source_type == "github"

        # 4. Verify context persists through get_session
        retrieved_plan = mock_orchestrator.get_session(plan.session_id)
        assert len(retrieved_plan.external_contexts) == 1
        assert retrieved_plan.external_contexts[0].source_type == "github"

    def test_multiple_contexts_workflow(self, mock_orchestrator):
        """Test workflow with multiple external context sources"""
        # 1. Start session
        plan = mock_orchestrator.start_session("Build a REST API")

        # 2. Add GitHub context
        github_ctx = ExternalContext(
            source_type="github",
            content_summary="## GitHub Repo: api-project\nLanguage: Python"
        )
        plan = mock_orchestrator.add_external_context(plan.session_id, github_ctx)

        # 3. Add web search context
        search_ctx = ExternalContext(
            source_type="web_search",
            content_summary="## Web Search: FastAPI best practices\n..."
        )
        plan = mock_orchestrator.add_external_context(plan.session_id, search_ctx)

        # 4. Add file context
        file_ctx = ExternalContext(
            source_type="file_upload",
            content_summary="## Uploaded File: requirements.txt\n..."
        )
        plan = mock_orchestrator.add_external_context(plan.session_id, file_ctx)

        # 5. Verify all contexts present
        assert len(plan.external_contexts) == 3
        assert plan.external_contexts[0].source_type == "github"
        assert plan.external_contexts[1].source_type == "web_search"
        assert plan.external_contexts[2].source_type == "file_upload"

    def test_context_persistence_through_workflow(self, mock_orchestrator):
        """Test that contexts persist through the planning workflow"""
        # 1. Start with contexts
        contexts = [
            ExternalContext(source_type="github", content_summary="Repo info")
        ]
        plan = mock_orchestrator.start_session("Add tests", external_contexts=contexts)

        # 2. Verify contexts in initial plan
        assert len(plan.external_contexts) == 1

        # 3. Add more context later
        new_context = ExternalContext(
            source_type="web_search",
            content_summary="Testing best practices"
        )
        plan = mock_orchestrator.add_external_context(plan.session_id, new_context)

        # 4. Verify both contexts present
        assert len(plan.external_contexts) == 2

        # 5. Retrieve and verify
        retrieved = mock_orchestrator.get_session(plan.session_id)
        assert len(retrieved.external_contexts) == 2
