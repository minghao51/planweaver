"""
Memory Layer with Embedding-Based Retrieval

Enables semantic search across historical plans to inform future planning.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from .models.plan import Plan
from .services.llm_gateway import LLMGateway


logger = logging.getLogger(__name__)


class MemorySearchQuery(BaseModel):
    """Query for searching similar historical plans."""

    query: str
    limit: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class MemoryResult(BaseModel):
    """Result from memory search with similarity score."""

    session_id: str
    user_intent: str
    similarity_score: float
    plan_snapshot: Dict[str, Any]
    created_at: datetime


class MemoryLayer:
    """
    Memory layer for semantic search across historical plans.

    Uses embedding-based similarity search to find relevant past plans
    that can inform current planning. Falls back to keyword search if
    embedding API fails.
    """

    def __init__(self, llm_gateway: LLMGateway, db_session: Session):
        self.llm = llm_gateway
        self.db = db_session
        self._embedding_model = "text-embedding-3-small"  # Default fallback

    async def search_similar_plans(self, query: MemorySearchQuery) -> List[MemoryResult]:
        """
        Search for similar historical plans using embedding-based similarity.

        Args:
            query: Search query with text, limit, and similarity threshold

        Returns:
            List of MemoryResult objects sorted by similarity score
        """
        try:
            # Generate embedding for search query
            query_embedding = await self._generate_embedding(query.query)

            if not query_embedding:
                logger.warning("Failed to generate query embedding, falling back to keyword search")
                return await self._keyword_search(query)

            # Fetch all stored embeddings
            results = await self._search_by_embedding(query_embedding, query.limit, query.similarity_threshold)

            return results

        except Exception as e:
            logger.warning(f"Embedding search failed: {e}, falling back to keyword search")
            return await self._keyword_search(query)

    async def index_session(self, plan: Plan) -> None:
        """
        Index a plan for future similarity search.

        Generates embedding for user_intent and stores it in the database.

        Args:
            plan: Plan to index
        """
        try:
            # Check if already indexed
            existing = self._get_embedding(plan.session_id)
            if existing:
                logger.debug(f"Session {plan.session_id} already indexed, skipping")
                return

            # Generate embedding for user intent
            embedding = await self._generate_embedding(plan.user_intent)

            if not embedding:
                logger.warning(f"Failed to generate embedding for session {plan.session_id}, skipping")
                return

            # Store embedding in database
            self._save_embedding(plan.session_id, plan.user_intent, embedding)

            logger.debug(f"Indexed session {plan.session_id} in memory layer")

        except Exception as e:
            logger.warning(f"Failed to index session {plan.session_id}: {e}")

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using Qwen embedding API.

        Args:
            text: Text to embed

        Returns:
            List of embedding floats or None if generation fails
        """
        try:
            from openai import OpenAI
            from .config import get_settings

            settings = get_settings()

            # Check if Qwen API key is configured
            if not settings.dashscope_api_key:
                logger.warning("Dashscope API key not configured, using fallback embedding")
                return self._generate_fallback_embedding(text)

            # Create OpenAI client for Qwen API
            client = OpenAI(api_key=settings.dashscope_api_key, base_url=settings.qwen_base_url)

            # Generate embedding using Qwen model
            response = client.embeddings.create(
                model=settings.embedding_model,
                input=text,
                dimensions=768,  # Qwen text-embedding-v4 uses 768 dimensions
            )

            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Qwen embedding generation failed: {e}, using fallback")
            return self._generate_fallback_embedding(text)

    def _generate_fallback_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate fallback embedding using hash-based approach.

        This is used when the embedding API is unavailable.
        Note: This provides deterministic but NOT semantically meaningful embeddings.

        Args:
            text: Text to embed

        Returns:
            List of embedding floats or None if generation fails
        """
        try:
            import numpy as np

            # Create a deterministic hash-based embedding
            hash_value = abs(hash(text)) % (2**32)
            embedding = np.random.RandomState(hash_value).random(768).tolist()

            logger.debug("Using fallback hash-based embedding (not semantically meaningful)")
            return embedding

        except Exception as e:
            logger.error(f"Fallback embedding generation failed: {e}")
            return None

    async def _search_by_embedding(
        self, query_embedding: List[float], limit: int, threshold: float
    ) -> List[MemoryResult]:
        """
        Search for similar plans using cosine similarity.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            threshold: Minimum similarity score

        Returns:
            List of MemoryResult objects
        """
        import numpy as np

        try:
            # Fetch all embeddings from database
            result = self.db.execute(
                text("""
                SELECT
                    pe.session_id,
                    pe.user_intent_embedding,
                    s.user_intent,
                    s.status,
                    s.created_at
                FROM plan_embeddings pe
                JOIN sessions s ON pe.session_id = s.id
                ORDER BY s.created_at DESC
                LIMIT 100
            """)
            )

            rows = result.fetchall()

            similarities = []
            query_vec = np.array(query_embedding)

            for row in rows:
                session_id, embedding_blob, user_intent, status, created_at = row

                # Deserialize embedding
                try:
                    stored_embedding = self._deserialize_embedding(embedding_blob)
                    if not stored_embedding:
                        continue

                    stored_vec = np.array(stored_embedding)

                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_vec, stored_vec)

                    if similarity >= threshold:
                        similarities.append(
                            {
                                "session_id": session_id,
                                "user_intent": user_intent,
                                "similarity_score": float(similarity),
                                "created_at": created_at,
                            }
                        )

                except Exception as e:
                    logger.debug(f"Failed to process embedding for {session_id}: {e}")
                    continue

            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)

            results = []
            for sim in similarities[:limit]:
                # Fetch plan snapshot
                plan_snapshot = self._get_plan_snapshot(sim["session_id"])

                results.append(
                    MemoryResult(
                        session_id=sim["session_id"],
                        user_intent=sim["user_intent"],
                        similarity_score=sim["similarity_score"],
                        plan_snapshot=plan_snapshot,
                        created_at=sim["created_at"],
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Embedding search failed: {e}")
            return []

    async def _keyword_search(self, query: MemorySearchQuery) -> List[MemoryResult]:
        """
        Fallback keyword search using SQL LIKE.

        Args:
            query: Search query

        Returns:
            List of MemoryResult objects
        """
        try:
            search_term = f"%{query.query.lower()}%"

            result = self.db.execute(
                text("""
                SELECT
                    id,
                    user_intent,
                    status,
                    created_at
                FROM sessions
                WHERE LOWER(user_intent) LIKE :search_term
                ORDER BY created_at DESC
                LIMIT :limit
            """),
                {"search_term": search_term, "limit": query.limit},
            )

            rows = result.fetchall()

            results = []
            for row in rows:
                session_id, user_intent, status, created_at = row
                plan_snapshot = self._get_plan_snapshot(session_id)

                # Use 0.5 as default similarity for keyword matches
                results.append(
                    MemoryResult(
                        session_id=session_id,
                        user_intent=user_intent,
                        similarity_score=0.5,
                        plan_snapshot=plan_snapshot,
                        created_at=created_at,
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _get_embedding(self, session_id: str) -> Optional[bytes]:
        """Get existing embedding for session."""
        try:
            result = self.db.execute(
                text("""
                SELECT user_intent_embedding
                FROM plan_embeddings
                WHERE session_id = :session_id
            """),
                {"session_id": session_id},
            )

            row = result.fetchone()
            return row[0] if row else None

        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None

    def _save_embedding(self, session_id: str, user_intent: str, embedding: List[float]) -> None:
        """Save embedding to database."""
        try:
            embedding_blob = self._serialize_embedding(embedding)

            self.db.execute(
                text("""
                INSERT INTO plan_embeddings (id, session_id, user_intent_embedding, created_at)
                VALUES (
                    lower(hex(randomblob(16))),
                    :session_id,
                    :embedding,
                    :created_at
                )
            """),
                {"session_id": session_id, "embedding": embedding_blob, "created_at": datetime.now(timezone.utc)},
            )

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save embedding: {e}")
            raise

    def _serialize_embedding(self, embedding: List[float]) -> bytes:
        """Serialize embedding list to bytes for storage."""
        import json

        return json.dumps(embedding).encode("utf-8")

    def _deserialize_embedding(self, blob: bytes) -> Optional[List[float]]:
        """Deserialize embedding bytes to list."""
        try:
            import json

            return json.loads(blob.decode("utf-8"))
        except Exception:
            return None

    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _get_plan_snapshot(self, session_id: str) -> Dict[str, Any]:
        """Get lightweight plan snapshot for memory result."""
        try:
            result = self.db.execute(
                text("""
                SELECT
                    id,
                    user_intent,
                    scenario_name,
                    status,
                    created_at,
                    updated_at,
                    metadata
                FROM sessions
                WHERE id = :session_id
            """),
                {"session_id": session_id},
            )

            row = result.fetchone()
            if not row:
                return {}

            return {
                "session_id": row[0],
                "user_intent": row[1],
                "scenario_name": row[2],
                "status": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "updated_at": row[5].isoformat() if row[5] else None,
                "planning_mode": (row[6] or {}).get("planning_mode", "baseline")
                if isinstance(row[6], dict)
                else "baseline",
            }

        except Exception as e:
            logger.debug(f"Failed to get plan snapshot: {e}")
            return {}
