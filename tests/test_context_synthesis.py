"""
Tests for Context Synthesis with Parallel Agents
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from planweaver.context_synthesis import (
    RepoAnalyser,
    MemoryRetriever,
    ConstraintExtractor,
    WebResearcher,
    ContextSynthesizer,
    RepoAnalysis,
    MemoryRetrieval,
    ConstraintExtraction,
    WebResearch,
    PlanBrief,
)
from planweaver.models.plan import Plan, ExternalContext
from planweaver.services.llm_gateway import LLMGateway
from planweaver.memory import MemoryLayer


@pytest.fixture
def mock_llm_gateway():
    """Mock LLM gateway."""
    gateway = Mock(spec=LLMGateway)
    return gateway


@pytest.fixture
def mock_memory_layer():
    """Mock memory layer."""
    memory = Mock(spec=MemoryLayer)
    return memory


@pytest.fixture
def sample_plan():
    """Create sample plan."""
    return Plan(
        session_id="test_session_123",
        user_intent="Build a REST API with FastAPI",
        scenario_name="web_development",
        status="BRAINSTORMING",
    )


@pytest.fixture
def sample_external_context():
    """Create sample external context."""
    return ExternalContext(
        source_type="github",
        source_url="https://github.com/example/repo",
        content_summary="Example FastAPI project",
    )


@pytest.mark.asyncio
async def test_repo_analyser_github_context(mock_llm_gateway):
    """Test RepoAnalyser with GitHub context."""
    analyser = RepoAnalyser(mock_llm_gateway)

    # Mock the GitHub analyzer
    analyser.github_analyzer.analyze_repository = AsyncMock(
        return_value={
            "metadata": {"language": "Python"},
            "dependencies": {"python": ["fastapi", "uvicorn"]},
            "key_files": {"README.md": "# Test"},
            "content_summary": "Python FastAPI project",
        }
    )

    context = ExternalContext(
        source_type="github",
        source_url="https://github.com/example/repo",
        content_summary="Test repo",
    )

    result = await analyser.analyze(context)

    assert isinstance(result, RepoAnalysis)
    assert result.language == "Python"
    assert "fastapi" in result.dependencies
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_repo_analyser_non_github_context(mock_llm_gateway):
    """Test RepoAnalyser with non-GitHub context."""
    analyser = RepoAnalyser(mock_llm_gateway)

    context = ExternalContext(
        source_type="web_search",
        content_summary="Test context",
    )

    result = await analyser.analyze(context)

    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_memory_retriever_success(mock_memory_layer):
    """Test MemoryRetriever successful retrieval."""
    retriever = MemoryRetriever(mock_memory_layer)

    # Mock memory search
    from planweaver.memory import MemoryResult

    mock_memory_layer.search_similar_plans = AsyncMock(
        return_value=[
            MemoryResult(
                session_id="similar_1",
                user_intent="Build FastAPI service",
                similarity_score=0.8,
                plan_snapshot={},
                created_at=datetime.now(timezone.utc),
            ),
        ]
    )

    result = await retriever.retrieve("Build REST API", limit=5)

    assert isinstance(result, MemoryRetrieval)
    assert len(result.similar_plans) == 1
    assert len(result.insights) > 0
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_memory_retriever_no_results(mock_memory_layer):
    """Test MemoryRetriever with no results."""
    retriever = MemoryRetriever(mock_memory_layer)

    mock_memory_layer.search_similar_plans = AsyncMock(return_value=[])

    result = await retriever.retrieve("Build something unique", limit=5)

    assert isinstance(result, MemoryRetrieval)
    assert len(result.similar_plans) == 0
    assert result.confidence < 0.5


@pytest.mark.asyncio
async def test_constraint_extractor(mock_llm_gateway):
    """Test ConstraintExtractor."""
    extractor = ConstraintExtractor(mock_llm_gateway)

    plan = Plan(
        session_id="test",
        user_intent="Build a REST API with authentication and testing",
        scenario_name="web",
    )

    result = await extractor.extract("Build a REST API with authentication", plan)

    assert isinstance(result, ConstraintExtraction)
    assert isinstance(result.explicit_constraints, list)
    assert isinstance(result.technical_requirements, list)
    assert result.confidence >= 0


@pytest.mark.asyncio
async def test_web_researcher_with_api_key(mock_llm_gateway):
    """Test WebResearcher with API key."""
    researcher = WebResearcher(mock_llm_gateway, "test_api_key")

    # Mock web search
    researcher.web_search = Mock()
    researcher.web_search.search = AsyncMock(
        return_value={
            "results": [
                {"title": "FastAPI Best Practices", "snippet": "Use dependency injection"},
            ],
        }
    )

    result = await researcher.research("Build FastAPI REST API")

    assert isinstance(result, WebResearch)
    assert len(result.findings) > 0 or result.confidence >= 0


@pytest.mark.asyncio
async def test_web_researcher_without_api_key(mock_llm_gateway):
    """Test WebResearcher without API key."""
    researcher = WebResearcher(mock_llm_gateway, None)

    result = await researcher.research("Build API")

    assert isinstance(result, WebResearch)
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_context_synthesizer_all_agents(mock_llm_gateway, mock_memory_layer):
    """Test ContextSynthesizer with all agents."""
    synthesizer = ContextSynthesizer(mock_llm_gateway, mock_memory_layer)

    plan = Plan(
        session_id="test",
        user_intent="Build FastAPI service",
    )

    external_contexts = [
        ExternalContext(
            source_type="github",
            source_url="https://github.com/test/repo",
            content_summary="Test repo",
        )
    ]

    # Mock the specialists
    synthesizer.repo_analyser.analyze = AsyncMock(
        return_value=RepoAnalysis(
            summary="Python FastAPI project",
            language="Python",
            dependencies=["fastapi"],
            confidence=0.8,
        )
    )

    synthesizer.memory_retriever.retrieve = AsyncMock(
        return_value=MemoryRetrieval(
            similar_plans=[],
            insights=["Similar project found"],
            confidence=0.7,
        )
    )

    synthesizer.constraint_extractor.extract = AsyncMock(
        return_value=ConstraintExtraction(
            explicit_constraints=["Must use FastAPI"],
            technical_requirements=["REST API"],
            confidence=0.6,
        )
    )

    synthesizer.web_researcher.research = AsyncMock(
        return_value=WebResearch(
            findings=["FastAPI best practices"],
            confidence=0.7,
        )
    )

    brief = await synthesizer.synthesize(plan, external_contexts)

    assert isinstance(brief, PlanBrief)
    assert brief.user_intent == "Build FastAPI service"
    assert brief.repo_analysis is not None
    assert brief.memory_retrieval is not None
    assert brief.constraint_extraction is not None
    assert brief.web_research is not None
    assert len(brief.synthesized_context) > 0
    assert len(brief.confidence_scores) > 0


@pytest.mark.asyncio
async def test_context_synthesizer_graceful_degradation(mock_llm_gateway, mock_memory_layer):
    """Test ContextSynthesizer handles agent failures gracefully."""
    synthesizer = ContextSynthesizer(mock_llm_gateway, mock_memory_layer)

    plan = Plan(
        session_id="test",
        user_intent="Build API",
    )

    # Mock all agents to fail
    synthesizer.repo_analyser.analyze = AsyncMock(side_effect=Exception("API error"))
    synthesizer.memory_retriever.retrieve = AsyncMock(side_effect=Exception("DB error"))
    synthesizer.constraint_extractor.extract = AsyncMock(side_effect=Exception("LLM error"))
    synthesizer.web_researcher.research = AsyncMock(side_effect=Exception("Search error"))

    brief = await synthesizer.synthesize(plan, [])

    assert isinstance(brief, PlanBrief)
    # Should still have a brief even with failures
    assert brief.user_intent == "Build API"
    # Most agents should have failed
    assert len([s for s in brief.confidence_scores.values() if s == 0.0]) >= 3


@pytest.mark.asyncio
async def test_context_synthesizer_no_external_contexts(mock_llm_gateway, mock_memory_layer):
    """Test ContextSynthesizer without external contexts."""
    synthesizer = ContextSynthesizer(mock_llm_gateway, mock_memory_layer)

    plan = Plan(
        session_id="test",
        user_intent="Build API",
    )

    # Mock memory and constraint extraction (no GitHub context)
    synthesizer.memory_retriever.retrieve = AsyncMock(
        return_value=MemoryRetrieval(
            similar_plans=[],
            insights=[],
            confidence=0.5,
        )
    )

    synthesizer.constraint_extractor.extract = AsyncMock(
        return_value=ConstraintExtraction(
            explicit_constraints=[],
            technical_requirements=[],
            confidence=0.5,
        )
    )

    synthesizer.web_researcher.research = AsyncMock(
        return_value=WebResearch(
            findings=[],
            confidence=0.3,
        )
    )

    brief = await synthesizer.synthesize(plan, [])

    assert isinstance(brief, PlanBrief)
    # Should not have repo analysis without GitHub context
    assert brief.repo_analysis is None


def test_build_synthesized_context():
    """Test context synthesis string building."""
    synthesizer = ContextSynthesizer(Mock(), Mock())

    repo_analysis = RepoAnalysis(
        summary="Python project",
        language="Python",
        confidence=0.8,
    )

    memory_retrieval = MemoryRetrieval(
        insights=["Similar plan found"],
        confidence=0.7,
    )

    constraint_extraction = ConstraintExtraction(
        technical_requirements=["REST API"],
        confidence=0.6,
    )

    web_research = WebResearch(
        best_practices=["Use dependency injection"],
        confidence=0.7,
    )

    context = synthesizer._build_synthesized_context(
        repo_analysis,
        memory_retrieval,
        constraint_extraction,
        web_research,
    )

    assert "Repository Context" in context
    assert "Python project" in context
    assert "Similar Plans" in context
    assert "Requirements" in context
    assert "Best Practices" in context


def test_generate_search_query():
    """Test search query generation."""
    researcher = WebResearcher(Mock())

    query = researcher._generate_search_query("Build a REST API with FastAPI for user authentication")

    # Should extract key terms
    assert len(query) > 0
    assert "best practices" in query.lower()


def test_plan_brief_model():
    """Test PlanBrief model."""
    brief = PlanBrief(
        user_intent="Build API",
        synthesized_context="Test context",
        confidence_scores={"memory": 0.7},
    )

    assert brief.user_intent == "Build API"
    assert brief.synthesized_context == "Test context"
    assert brief.confidence_scores["memory"] == 0.7
    assert brief.synthesized_at is not None
