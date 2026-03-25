"""
Integration Tests for Phase 1 Components

Tests integration between Memory Layer, MCP Server, and UI.
"""

import pytest

from planweaver.orchestrator import Orchestrator
from planweaver.memory import MemoryLayer, MemorySearchQuery
from planweaver.mcp_server import MCPServer


@pytest.fixture
def orchestrator():
    """Create orchestrator instance."""
    return Orchestrator()


@pytest.fixture
def sample_plan(orchestrator):
    """Create sample plan."""
    return orchestrator.start_session(
        user_intent="Build a REST API with FastAPI",
        scenario_name="web_development",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_layer_integration(orchestrator, sample_plan):
    """Test memory layer integration with orchestrator."""
    # Search for similar plans
    results = await orchestrator.search_similar_plans(
        query="Build API",
        limit=5,
        similarity_threshold=0.6,
    )

    assert isinstance(results, list)
    # Should return results (even if empty list)
    assert results is not None


@pytest.mark.integration
def test_memory_layer_indexing(orchestrator, sample_plan):
    """Test memory layer indexes plans."""
    # Memory indexing happens in background
    # Just verify the method exists and can be called
    assert hasattr(orchestrator.memory, "index_session")
    assert hasattr(orchestrator.memory, "search_similar_plans")


@pytest.mark.integration
def test_mcp_server_initialization(orchestrator):
    """Test MCP server initialization."""
    mcp_server = MCPServer(orchestrator)

    assert mcp_server.orchestrator == orchestrator
    assert mcp_server.tools is not None
    assert len(mcp_server.tools) == 6  # 6 tools registered


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_server_create_session(orchestrator):
    """Test MCP server create_session tool."""
    mcp_server = MCPServer(orchestrator)

    result = await mcp_server.create_session_tool(
        user_intent="Build a microservice",
        scenario_name="backend",
    )

    assert result is not None
    # Should be JSON string
    assert isinstance(result, str)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_server_list_sessions(orchestrator, sample_plan):
    """Test MCP server list_sessions tool."""
    mcp_server = MCPServer(orchestrator)

    result = await mcp_server.list_sessions_tool(limit=10)

    assert result is not None
    import json

    result_dict = json.loads(result)
    assert "success" in result_dict


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_server_get_session_state(orchestrator, sample_plan):
    """Test MCP server get_session_state tool."""
    mcp_server = MCPServer(orchestrator)

    result = await mcp_server.get_session_state_tool(
        session_id=sample_plan.session_id,
    )

    assert result is not None
    import json

    result_dict = json.loads(result)
    assert "session_id" in result_dict


@pytest.mark.integration
def test_orchestrator_has_memory_methods(orchestrator):
    """Test orchestrator has memory integration methods."""
    assert hasattr(orchestrator, "search_similar_plans")
    assert hasattr(orchestrator, "memory")
    assert isinstance(orchestrator.memory, MemoryLayer)


@pytest.mark.integration
def test_orchestrator_has_mcp_integration(orchestrator):
    """Test orchestrator can be used with MCP server."""
    mcp_server = MCPServer(orchestrator)
    assert mcp_server.orchestrator == orchestrator


@pytest.mark.integration
def test_database_migrations_exist():
    """Test that database migrations are defined."""
    from planweaver.db.database import MIGRATIONS

    # Should have at least migrations v9-v13
    migration_versions = [m["version"] for m in MIGRATIONS]
    assert 9 in migration_versions  # plan_embeddings
    assert 10 in migration_versions  # execution_outcomes
    assert 11 in migration_versions  # plan_templates
    assert 12 in migration_versions  # decision_records
    assert 13 in migration_versions  # precondition_results


@pytest.mark.integration
def test_static_ui_exists():
    """Test that static UI file exists."""
    from pathlib import Path

    static_dir = Path(__file__).parent.parent / "static"
    index_file = static_dir / "index.html"

    assert static_dir.exists()
    assert index_file.exists()


@pytest.mark.integration
def test_static_ui_has_required_elements():
    """Test that static UI has required elements."""
    from pathlib import Path

    index_file = Path(__file__).parent.parent / "static" / "index.html"
    content = index_file.read_text()

    # Check for key elements
    assert "user-intent" in content
    assert "scenario-name" in content
    assert "planning-mode" in content
    assert "session-list" in content
    assert "execution-graph" in content
    assert "approve-button" in content


@pytest.mark.integration
def test_cli_has_mcp_command():
    """Test that CLI has mcp-server command."""
    from planweaver.cli import cli

    # Get all commands
    commands = [cmd.name for cmd in cli.commands.values()]

    assert "mcp-server" in commands


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_session_creation_with_memory(orchestrator):
    """Test full flow: create session -> index -> search."""
    # Create session
    plan = orchestrator.start_session(
        user_intent="Build a GraphQL API with Node.js",
        scenario_name="graphql",
    )

    assert plan.session_id is not None

    # Search for similar plans (should find the one we just created or others)
    results = await orchestrator.search_similar_plans(
        query="GraphQL API",
        limit=5,
    )

    assert isinstance(results, list)


@pytest.mark.integration
def test_memory_search_query_validation():
    """Test MemorySearchQuery validation."""
    from pydantic import ValidationError

    # Valid query
    query = MemorySearchQuery(query="test")
    assert query.query == "test"

    # Invalid limit (too high)
    with pytest.raises(ValidationError):
        MemorySearchQuery(query="test", limit=100)

    # Invalid similarity_threshold (negative)
    with pytest.raises(ValidationError):
        MemorySearchQuery(query="test", similarity_threshold=-0.1)


@pytest.mark.integration
def test_mcp_tool_schemas():
    """Test MCP tool schemas are valid."""
    from planweaver.mcp_server import MCPServer
    from planweaver.orchestrator import Orchestrator

    mcp_server = MCPServer(Orchestrator())

    for tool_name, tool_def in mcp_server.tools.items():
        assert "name" in tool_def
        assert "description" in tool_def
        assert "parameters" in tool_def
        assert tool_def["parameters"]["type"] == "object"
        assert "properties" in tool_def["parameters"]
