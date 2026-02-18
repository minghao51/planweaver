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
async def test_add_web_search_context(context_service, mocker):
    """Test adding web search context"""
    # Skip if not configured
    if not context_service.web_search:
        pytest.skip("Tavily API key not configured")

    # Mock the search service
    mock_results = {
        "query": "FastAPI best practices",
        "results": [
            {"title": "FastAPI Guide", "url": "https://example.com", "snippet": "Best practices..."}
        ],
        "answer": "FastAPI is a modern web framework",
        "summary": "## Web Search Results..."
    }

    mocker.patch.object(
        context_service.web_search,
        "search",
        new=mocker.AsyncMock(return_value=mock_results)
    )

    context = await context_service.add_web_search_context("FastAPI best practices")

    assert context.source_type == "web_search"
    assert "FastAPI" in context.content_summary
    assert context.metadata["query"] == "FastAPI best practices"


@pytest.mark.asyncio
async def test_web_search_not_configured(context_service):
    """Test web search raises ValueError when not configured"""
    # Temporarily remove web_search to simulate missing API key
    original_web_search = context_service.web_search
    context_service.web_search = None

    try:
        with pytest.raises(ValueError, match="Web search not configured"):
            await context_service.add_web_search_context("test query")
    finally:
        context_service.web_search = original_web_search


@pytest.mark.asyncio
async def test_add_file_context_text(context_service):
    """Test adding text file context"""
    content = b"Hello, this is a test file with some content."

    context = await context_service.add_file_context("test.txt", content)

    assert context.source_type == "file_upload"
    assert "test.txt" in context.content_summary
    assert context.metadata["filename"] == "test.txt"
    assert context.metadata["file_type"] == ".txt"


@pytest.mark.asyncio
async def test_add_file_context_pdf(context_service):
    """Test adding PDF file context"""
    # Create minimal PDF (for testing)
    from PyPDF2 import PdfWriter
    import io

    pdf_writer = PdfWriter()
    pdf_writer.add_blank_page(width=200, height=200)

    pdf_bytes = io.BytesIO()
    pdf_writer.write(pdf_bytes)
    content = pdf_bytes.getvalue()

    context = await context_service.add_file_context("test.pdf", content)

    assert context.source_type == "file_upload"
    assert context.metadata["file_type"] == ".pdf"


@pytest.mark.asyncio
async def test_file_too_large(context_service):
    """Test file size validation"""
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB

    with pytest.raises(ValueError, match="File too large"):
        await context_service.add_file_context("large.txt", large_content)


@pytest.mark.asyncio
async def test_unsupported_file_type(context_service):
    """Test file type validation"""
    content = b"some content"

    with pytest.raises(ValueError, match="Unsupported file type"):
        await context_service.add_file_context("test.exe", content)


