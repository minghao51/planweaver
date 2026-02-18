import pytest
from unittest.mock import Mock, patch, AsyncMock
from planweaver.services.context_service import ContextService
from planweaver.config import Settings
from planweaver.services.llm_gateway import LLMGateway


@pytest.fixture
def context_service(settings, llm_gateway):
    return ContextService(settings, llm_gateway)


@pytest.mark.asyncio
async def test_context_service_creation(context_service):
    """Test that context service can be instantiated"""
    assert context_service is not None
    assert context_service.config is not None
    assert context_service.llm is not None
    assert context_service.github_analyzer is not None


@pytest.mark.asyncio
async def test_add_github_context(context_service, mocker):
    """Test adding GitHub context"""
    # Mock the analyzer
    mock_analysis = {
        "metadata": {"name": "test-repo", "description": "Test", "language": "Python", "stars": 100, "url": "https://github.com/test/repo"},
        "file_structure": ["README.md (1000 bytes)", "main.py (500 bytes)"],
        "key_files": {"README.md": "Test README"},
        "dependencies": {"python": ["requests", "fastapi"], "javascript": [], "other": []},
        "content_summary": "## GitHub Repository: test-repo\n..."
    }

    mocker.patch.object(
        context_service.github_analyzer,
        "analyze_repository",
        new=AsyncMock(return_value=mock_analysis)
    )

    context = await context_service.add_github_context("https://github.com/test/repo")

    assert context.source_type == "github"
    assert context.source_url == "https://github.com/test/repo"
    assert "test-repo" in context.content_summary
    assert context.metadata["repo_name"] == "test-repo"


@pytest.mark.asyncio
async def test_web_search_not_implemented(context_service):
    """Test web search raises NotImplementedError"""
    with pytest.raises(NotImplementedError):
        await context_service.add_web_search_context("test query")


@pytest.mark.asyncio
async def test_file_context_not_implemented(context_service):
    """Test file context raises NotImplementedError"""
    with pytest.raises(NotImplementedError):
        await context_service.add_file_context("test.txt", b"content")

