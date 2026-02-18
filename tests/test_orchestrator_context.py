import pytest
from unittest.mock import Mock, patch, MagicMock
from planweaver.models.plan import ExternalContext, Plan, PlanStatus
from planweaver.orchestrator import Orchestrator


@pytest.fixture
def mock_orchestrator():
    """Create orchestrator with mocked planner for testing"""
    with patch("planweaver.orchestrator.Planner") as mock_planner_class:
        # Create mock planner
        mock_planner = Mock()
        mock_planner.create_initial_plan.return_value = Plan(
            session_id="test-123",
            status=PlanStatus.BRAINSTORMING,
            user_intent="Test intent"
        )
        mock_planner_class.return_value = mock_planner

        # Create orchestrator
        orchestrator = Orchestrator()
        yield orchestrator


def test_add_external_context(mock_orchestrator):
    """Test adding external context to a session"""
    # Create a session
    plan = mock_orchestrator.start_session("Test intent")

    # Create context
    context = ExternalContext(
        source_type="github",
        content_summary="Test repo content"
    )

    # Add context
    updated_plan = mock_orchestrator.add_external_context(plan.session_id, context)

    # Verify
    assert len(updated_plan.external_contexts) == 1
    assert updated_plan.external_contexts[0].source_type == "github"


def test_start_session_with_contexts(mock_orchestrator):
    """Test starting session with external contexts"""
    contexts = [
        ExternalContext(source_type="github", content_summary="Repo 1"),
        ExternalContext(source_type="web_search", content_summary="Search results")
    ]

    plan = mock_orchestrator.start_session("Test intent", external_contexts=contexts)

    assert len(plan.external_contexts) == 2


def test_add_multiple_contexts(mock_orchestrator):
    """Test adding multiple contexts to a session"""
    plan = mock_orchestrator.start_session("Test intent")

    # Add first context
    context1 = ExternalContext(source_type="github", content_summary="Repo 1")
    plan = mock_orchestrator.add_external_context(plan.session_id, context1)

    # Add second context
    context2 = ExternalContext(source_type="web_search", content_summary="Search")
    plan = mock_orchestrator.add_external_context(plan.session_id, context2)

    # Verify both are present
    assert len(plan.external_contexts) == 2
    assert plan.external_contexts[0].source_type == "github"
    assert plan.external_contexts[1].source_type == "web_search"


def test_get_session_includes_contexts(mock_orchestrator):
    """Test that get_session loads external contexts"""
    contexts = [
        ExternalContext(source_type="file_upload", content_summary="File content")
    ]

    plan = mock_orchestrator.start_session("Test", external_contexts=contexts)
    retrieved_plan = mock_orchestrator.get_session(plan.session_id)

    assert len(retrieved_plan.external_contexts) == 1
    assert retrieved_plan.external_contexts[0].source_type == "file_upload"
