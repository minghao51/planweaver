import pytest
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


@pytest.mark.asyncio
async def test_github_context_not_implemented(context_service):
    """Test GitHub context raises NotImplementedError"""
    with pytest.raises(NotImplementedError):
        await context_service.add_github_context("https://github.com/test/repo")


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
