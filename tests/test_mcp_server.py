"""
Tests for MCP Server for Agent Communication
"""

import pytest
from unittest.mock import Mock, AsyncMock
import json

from planweaver.mcp_server import MCPServer, MCPRequest, MCPResponse, MCPError


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator."""
    orchestrator = Mock()
    return orchestrator


@pytest.fixture
def mcp_server(mock_orchestrator):
    """Create MCP server instance."""
    return MCPServer(mock_orchestrator)


@pytest.fixture
def sample_plan():
    """Sample plan for testing."""
    plan = Mock()
    plan.session_id = "test_session_123"
    plan.status = Mock(value="BRAINSTORMING")
    plan.user_intent = "Build a REST API"
    plan.scenario_name = "web_dev"
    plan.open_questions = []
    plan.candidate_plans = []
    plan.execution_graph = []
    plan.selected_candidate_id = None
    plan.approved_candidate_id = None
    plan.created_at = Mock(isoformat=Mock(return_value="2024-01-01T00:00:00"))
    plan.updated_at = Mock(isoformat=Mock(return_value="2024-01-01T01:00:00"))
    return plan


def test_mcp_server_initialization(mcp_server):
    """Test MCP server initialization."""
    assert mcp_server.orchestrator is not None
    assert mcp_server.tools is not None
    assert isinstance(mcp_server.tools, dict)


def test_mcp_server_tools_registration(mcp_server):
    """Test that all expected tools are registered."""
    tools = mcp_server.tools

    assert "create_session" in tools
    assert "send_message" in tools
    assert "get_session_state" in tools
    assert "approve_plan" in tools
    assert "list_sessions" in tools
    assert "get_similar_plans" in tools


def test_tool_schema_structure(mcp_server):
    """Test that tool schemas have correct structure."""
    for tool_name, tool_def in mcp_server.tools.items():
        assert "name" in tool_def
        assert "description" in tool_def
        assert "parameters" in tool_def
        assert tool_def["parameters"]["type"] == "object"
        assert "properties" in tool_def["parameters"]


@pytest.mark.asyncio
async def test_create_session_tool(mcp_server, mock_orchestrator, sample_plan):
    """Test create_session tool."""
    mock_orchestrator.start_session = Mock(return_value=sample_plan)

    result = await mcp_server.create_session_tool(
        user_intent="Build a REST API",
        scenario_name="web_dev",
    )

    result_dict = json.loads(result)

    assert result_dict["success"] is True
    assert result_dict["session_id"] == "test_session_123"
    assert result_dict["status"] == "BRAINSTORMING"
    assert result_dict["user_intent"] == "Build a REST API"


@pytest.mark.asyncio
async def test_create_session_tool_error(mcp_server, mock_orchestrator):
    """Test create_session tool with error."""
    mock_orchestrator.start_session = Mock(side_effect=Exception("Database error"))

    result = await mcp_server.create_session_tool(
        user_intent="Build a REST API",
    )

    result_dict = json.loads(result)

    assert result_dict["success"] is False
    assert "error" in result_dict


@pytest.mark.asyncio
async def test_send_message_tool(mcp_server, mock_orchestrator, sample_plan):
    """Test send_message tool."""
    mock_orchestrator.get_session = Mock(return_value=sample_plan)

    result = await mcp_server.send_message_tool(
        session_id="test_session_123",
        content="Add authentication",
        role="user",
    )

    result_dict = json.loads(result)

    assert result_dict["success"] is True
    assert result_dict["session_id"] == "test_session_123"


@pytest.mark.asyncio
async def test_send_message_tool_not_found(mcp_server, mock_orchestrator):
    """Test send_message tool with non-existent session."""
    mock_orchestrator.get_session = Mock(return_value=None)

    result = await mcp_server.send_message_tool(
        session_id="nonexistent",
        content="Test message",
    )

    result_dict = json.loads(result)

    assert result_dict["success"] is False
    assert "not found" in result_dict["error"].lower()


@pytest.mark.asyncio
async def test_get_session_state_tool(mcp_server, mock_orchestrator, sample_plan):
    """Test get_session_state tool."""
    mock_orchestrator.get_session = Mock(return_value=sample_plan)

    result = await mcp_server.get_session_state_tool(
        session_id="test_session_123",
    )

    result_dict = json.loads(result)

    assert result_dict["success"] is True
    assert result_dict["session_id"] == "test_session_123"
    assert result_dict["status"] == "BRAINSTORMING"
    assert result_dict["user_intent"] == "Build a REST API"


@pytest.mark.asyncio
async def test_approve_plan_tool(mcp_server, mock_orchestrator, sample_plan):
    """Test approve_plan tool."""
    mock_orchestrator.get_session = Mock(return_value=sample_plan)
    mock_orchestrator.approve_plan = Mock(return_value=sample_plan)

    result = await mcp_server.approve_plan_tool(
        session_id="test_session_123",
    )

    result_dict = json.loads(result)

    assert result_dict["success"] is True
    assert result_dict["session_id"] == "test_session_123"


@pytest.mark.asyncio
async def test_list_sessions_tool(sample_plan):
    """Test list_sessions tool."""
    from planweaver.mcp_server import MCPServer
    from unittest.mock import Mock

    mock_orchestrator = Mock()
    mock_orchestrator.list_sessions = Mock(
        return_value={
            "sessions": [sample_plan],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }
    )

    mcp_server = MCPServer(mock_orchestrator)

    result = await mcp_server.list_sessions_tool(
        limit=10,
        status="BRAINSTORMING",
    )

    result_dict = json.loads(result)

    assert result_dict["success"] is True
    assert "sessions" in result_dict
    assert result_dict["total"] == 1


@pytest.mark.asyncio
async def test_get_similar_plans_tool(mcp_server, mock_orchestrator, sample_plan):
    """Test get_similar_plans tool."""
    mock_orchestrator.get_session = Mock(return_value=sample_plan)
    mock_orchestrator.search_similar_plans = AsyncMock(
        return_value=[
            {
                "session_id": "similar_123",
                "user_intent": "Build API",
                "similarity_score": 0.85,
            }
        ]
    )

    result = await mcp_server.get_similar_plans_tool(
        session_id="test_session_123",
        query="API",
        limit=5,
    )

    result_dict = json.loads(result)

    assert result_dict["success"] is True
    assert result_dict["session_id"] == "test_session_123"
    assert "similar_plans" in result_dict


def test_create_server(mcp_server):
    """Test create_server method."""
    server = mcp_server.create_server()

    assert server["name"] == "planweaver-mcp-server"
    assert server["version"] == "0.1.0"
    assert "tools" in server


@pytest.mark.asyncio
async def test_handle_request_valid_method(mcp_server, mock_orchestrator, sample_plan):
    """Test handle_request with valid method."""
    mock_orchestrator.start_session = Mock(return_value=sample_plan)

    request = {
        "jsonrpc": "2.0",
        "method": "create_session",
        "params": {
            "user_intent": "Build API",
        },
        "id": "test_id",
    }

    response = await mcp_server.handle_request(request)
    response_dict = json.loads(response)

    assert response_dict["jsonrpc"] == "2.0"
    assert "result" in response_dict
    assert response_dict["id"] == "test_id"


@pytest.mark.asyncio
async def test_handle_request_invalid_method(mcp_server):
    """Test handle_request with invalid method."""
    request = {
        "jsonrpc": "2.0",
        "method": "invalid_method",
        "params": {},
        "id": "test_id",
    }

    response = await mcp_server.handle_request(request)
    response_dict = json.loads(response)

    assert response_dict["jsonrpc"] == "2.0"
    assert "error" in response_dict
    assert response_dict["error"]["code"] == -32601  # Method not found


@pytest.mark.asyncio
async def test_handle_request_exception(mcp_server, mock_orchestrator):
    """Test handle_request when tool raises exception."""
    mock_orchestrator.get_session = Mock(side_effect=Exception("Test error"))

    request = {
        "jsonrpc": "2.0",
        "method": "get_session_state",
        "params": {
            "session_id": "test",
        },
        "id": "test_id",
    }

    response = await mcp_server.handle_request(request)
    response_dict = json.loads(response)

    assert response_dict["jsonrpc"] == "2.0"
    # The error is in the result field, not at top level
    assert "result" in response_dict
    assert response_dict["result"]["success"] is False
    assert "error" in response_dict["result"]


def test_mcp_request_model():
    """Test MCPRequest model."""
    request = MCPRequest(
        method="create_session",
        params={"user_intent": "test"},
        id="123",
    )

    assert request.jsonrpc == "2.0"
    assert request.method == "create_session"
    assert request.params == {"user_intent": "test"}
    assert request.id == "123"


def test_mcp_response_model():
    """Test MCPResponse model."""
    response = MCPResponse(
        result={"success": True},
        id="123",
    )

    assert response.jsonrpc == "2.0"
    assert response.result == {"success": True}
    assert response.id == "123"


def test_mcp_response_with_error():
    """Test MCPResponse model with error."""
    response = MCPResponse(
        error={
            "code": -32601,
            "message": "Method not found",
        },
        id="123",
    )

    assert response.jsonrpc == "2.0"
    assert response.error is not None
    assert response.error["code"] == -32601
    assert response.result is None


def test_mcp_error_model():
    """Test MCPError model."""
    error = MCPError(
        code=-32601,
        message="Method not found",
        data="create_session",
    )

    assert error.code == -32601
    assert error.message == "Method not found"
    assert error.data == "create_session"
