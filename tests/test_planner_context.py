import pytest
from planweaver.models.plan import Plan, ExternalContext, PlanStatus
from planweaver.services.planner import Planner


@pytest.fixture
def planner(mock_llm_gateway):
    """Create planner with mocked LLM"""
    return Planner(llm_gateway=mock_llm_gateway)


def test_planner_includes_context_in_prompt(planner):
    """Test that external context is included in planner prompt"""
    # Create plan with context
    plan = Plan(
        session_id="test-123",
        status=PlanStatus.BRAINSTORMING,
        user_intent="Refactor this repo",
        external_contexts=[
            ExternalContext(
                source_type="github",
                content_summary="## GitHub Repo: test-repo\nLanguage: Python"
            )
        ]
    )

    prompt = planner._build_planner_prompt("Refactor this repo", plan)

    assert "AVAILABLE CONTEXT" in prompt
    assert "test-repo" in prompt
    assert "Language: Python" in prompt


def test_planner_without_context(planner):
    """Test planner without external context"""
    plan = Plan(
        session_id="test-123",
        status=PlanStatus.BRAINSTORMING,
        user_intent="Test intent",
        external_contexts=[]
    )

    prompt = planner._build_planner_prompt("Test intent", plan)

    assert "AVAILABLE CONTEXT" not in prompt
    assert "User Request: Test intent" in prompt


def test_planner_with_multiple_contexts(planner):
    """Test planner with multiple external contexts"""
    plan = Plan(
        session_id="test-123",
        status=PlanStatus.BRAINSTORMING,
        user_intent="Build API",
        external_contexts=[
            ExternalContext(
                source_type="github",
                content_summary="## GitHub Repo: my-app\nLanguage: TypeScript"
            ),
            ExternalContext(
                source_type="web_search",
                content_summary="## Web Search: FastAPI best practices\n..."
            )
        ]
    )

    prompt = planner._build_planner_prompt("Build API", plan)

    assert "Context Source 1 (GITHUB)" in prompt
    assert "Context Source 2 (WEB_SEARCH)" in prompt
    assert "my-app" in prompt
    assert "FastAPI" in prompt
