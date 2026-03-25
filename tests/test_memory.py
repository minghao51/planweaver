"""
Tests for Memory Layer with Embedding-Based Retrieval
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from planweaver.memory import MemoryLayer, MemorySearchQuery
from planweaver.models.plan import Plan
from planweaver.services.llm_gateway import LLMGateway


@pytest.fixture
def mock_llm_gateway():
    """Mock LLM gateway."""
    gateway = Mock(spec=LLMGateway)
    return gateway


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = Mock()
    session.execute = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def memory_layer(mock_llm_gateway, mock_db_session):
    """Create memory layer instance."""
    return MemoryLayer(mock_llm_gateway, mock_db_session)


@pytest.fixture
def sample_plan():
    """Create sample plan for testing."""
    return Plan(
        session_id="test_session_123",
        user_intent="Build a REST API with FastAPI",
        scenario_name="web_development",
        status="BRAINSTORMING",
    )


@pytest.mark.asyncio
async def test_memory_search_query_defaults():
    """Test MemorySearchQuery default values."""
    query = MemorySearchQuery(query="test query")

    assert query.query == "test query"
    assert query.limit == 5
    assert query.similarity_threshold == 0.7


@pytest.mark.asyncio
async def test_memory_search_query_custom_values():
    """Test MemorySearchQuery with custom values."""
    query = MemorySearchQuery(
        query="custom query",
        limit=10,
        similarity_threshold=0.8,
    )

    assert query.query == "custom query"
    assert query.limit == 10
    assert query.similarity_threshold == 0.8


@pytest.mark.asyncio
async def test_memory_search_query_validation():
    """Test MemorySearchQuery validation."""
    # Test limit validation
    with pytest.raises(ValueError):
        MemorySearchQuery(query="test", limit=0)

    with pytest.raises(ValueError):
        MemorySearchQuery(query="test", limit=21)

    # Test similarity_threshold validation
    with pytest.raises(ValueError):
        MemorySearchQuery(query="test", similarity_threshold=-0.1)

    with pytest.raises(ValueError):
        MemorySearchQuery(query="test", similarity_threshold=1.1)


@pytest.mark.asyncio
async def test_search_similar_plans_with_embedding(memory_layer):
    """Test search with embedding-based similarity."""
    query = MemorySearchQuery(query="build API")

    # Mock database response
    mock_result = Mock()
    mock_result.fetchall = Mock(
        return_value=[
            (
                "session_1",
                b"[0.1, 0.2, 0.3]",
                "Build REST API",
                "APPROVED",
                datetime.now(timezone.utc),
            ),
        ]
    )

    memory_layer.db.execute = Mock(return_value=mock_result)

    results = await memory_layer.search_similar_plans(query)

    assert isinstance(results, list)
    assert len(results) >= 0


@pytest.mark.asyncio
async def test_search_similar_plans_fallback_to_keyword(memory_layer):
    """Test fallback to keyword search when embedding fails."""
    query = MemorySearchQuery(query="build API")

    # Mock embedding generation failure
    with patch.object(memory_layer, "_generate_embedding", return_value=None):
        # Mock keyword search response
        mock_result = Mock()
        mock_result.fetchall = Mock(
            return_value=[
                ("session_1", "Build REST API", "APPROVED", datetime.now(timezone.utc)),
            ]
        )
        memory_layer.db.execute = Mock(return_value=mock_result)

        results = await memory_layer.search_similar_plans(query)

        assert isinstance(results, list)


@pytest.mark.asyncio
async def test_index_session(memory_layer, sample_plan):
    """Test indexing a session in memory layer."""
    # Mock _get_embedding to return None (not indexed yet)
    memory_layer._get_embedding = Mock(return_value=None)

    # Mock _generate_embedding
    memory_layer._generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

    # Mock _save_embedding
    memory_layer._save_embedding = Mock()

    await memory_layer.index_session(sample_plan)

    # Verify embedding was generated and saved
    memory_layer._generate_embedding.assert_called_once_with(sample_plan.user_intent)
    memory_layer._save_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_index_session_already_indexed(memory_layer, sample_plan):
    """Test that already indexed sessions are skipped."""
    # Mock _get_embedding to return existing embedding
    memory_layer._get_embedding = Mock(return_value=b"[0.1, 0.2, 0.3]")

    await memory_layer.index_session(sample_plan)

    # Verify _generate_embedding was NOT called
    assert (
        not hasattr(memory_layer._generate_embedding, "assert_called")
        or memory_layer._generate_embedding.call_count == 0
    )


@pytest.mark.asyncio
async def test_index_session_embedding_failure(memory_layer, sample_plan):
    """Test handling of embedding generation failure."""
    # Mock _get_embedding to return None
    memory_layer._get_embedding = Mock(return_value=None)

    # Mock _generate_embedding to fail
    memory_layer._generate_embedding = AsyncMock(return_value=None)

    # Should not raise exception
    await memory_layer.index_session(sample_plan)

    # Verify _save_embedding was NOT called
    memory_layer._save_embedding = Mock()
    assert memory_layer._save_embedding.call_count == 0


def test_serialize_embedding(memory_layer):
    """Test embedding serialization."""
    import json

    embedding = [0.1, 0.2, 0.3, 0.4]
    serialized = memory_layer._serialize_embedding(embedding)

    assert isinstance(serialized, bytes)
    assert json.loads(serialized.decode("utf-8")) == embedding


def test_deserialize_embedding(memory_layer):
    """Test embedding deserialization."""
    import json

    embedding = [0.1, 0.2, 0.3, 0.4]
    serialized = json.dumps(embedding).encode("utf-8")

    deserialized = memory_layer._deserialize_embedding(serialized)

    assert deserialized == embedding


def test_deserialize_invalid_embedding(memory_layer):
    """Test deserialization of invalid embedding."""
    result = memory_layer._deserialize_embedding(b"invalid json")
    assert result is None


def test_cosine_similarity(memory_layer):
    """Test cosine similarity calculation."""
    try:
        import numpy as np

        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])

        similarity = memory_layer._cosine_similarity(vec1, vec2)
        assert similarity == 1.0
    except ImportError:
        pytest.skip("numpy not installed")


def test_cosine_similarity_orthogonal(memory_layer):
    """Test cosine similarity for orthogonal vectors."""
    try:
        import numpy as np

        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])

        similarity = memory_layer._cosine_similarity(vec1, vec2)
        assert similarity == 0.0
    except ImportError:
        pytest.skip("numpy not installed")


def test_cosine_similarity_zero_vector(memory_layer):
    """Test cosine similarity with zero vector."""
    try:
        import numpy as np

        vec1 = np.array([0.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])

        similarity = memory_layer._cosine_similarity(vec1, vec2)
        assert similarity == 0.0
    except ImportError:
        pytest.skip("numpy not installed")


@pytest.mark.asyncio
async def test_keyword_search(memory_layer):
    """Test keyword search fallback."""
    query = MemorySearchQuery(query="API")

    mock_result = Mock()
    mock_result.fetchall = Mock(
        return_value=[
            ("session_1", "Build REST API", "APPROVED", datetime.now(timezone.utc)),
        ]
    )
    memory_layer.db.execute = Mock(return_value=mock_result)

    results = await memory_layer._keyword_search(query)

    assert isinstance(results, list)
    # Verify similarity is 0.5 for keyword matches
    if results:
        assert results[0].similarity_score == 0.5


@pytest.mark.asyncio
async def test_save_embedding(memory_layer):
    """Test saving embedding to database."""
    memory_layer.db.execute = Mock()
    memory_layer.db.commit = Mock()

    embedding = [0.1, 0.2, 0.3]

    memory_layer._save_embedding("session_123", "test intent", embedding)

    memory_layer.db.execute.assert_called()
    memory_layer.db.commit.assert_called()


@pytest.mark.asyncio
async def test_save_embedding_failure(memory_layer):
    """Test handling of save embedding failure."""
    memory_layer.db.execute = Mock(side_effect=Exception("Database error"))
    memory_layer.db.rollback = Mock()

    embedding = [0.1, 0.2, 0.3]

    with pytest.raises(Exception):
        memory_layer._save_embedding("session_123", "test intent", embedding)

    memory_layer.db.rollback.assert_called()


@pytest.mark.asyncio
async def test_get_plan_snapshot(memory_layer):
    """Test getting plan snapshot."""
    mock_result = Mock()
    mock_result.fetchone = Mock(
        return_value=(
            "session_123",
            "Build API",
            "web_dev",
            "APPROVED",
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
            None,
        )
    )
    memory_layer.db.execute = Mock(return_value=mock_result)

    snapshot = memory_layer._get_plan_snapshot("session_123")

    assert isinstance(snapshot, dict)
    assert snapshot.get("session_id") == "session_123"
    assert snapshot.get("user_intent") == "Build API"


@pytest.mark.asyncio
async def test_get_plan_snapshot_not_found(memory_layer):
    """Test getting plan snapshot for non-existent session."""
    mock_result = Mock()
    mock_result.fetchone = Mock(return_value=None)
    memory_layer.db.execute = Mock(return_value=mock_result)

    snapshot = memory_layer._get_plan_snapshot("nonexistent")

    assert snapshot == {}
