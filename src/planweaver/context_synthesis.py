"""
Context Synthesis with Parallel Agents

Replaces ad-hoc context assembly with 4 parallel specialist agents
that gather and synthesize context for planning.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .models.plan import Plan, ExternalContext
from .services.llm_gateway import LLMGateway
from .memory import MemoryLayer, MemorySearchQuery
from .services.github_analyzer import GitHubAnalyzer
from .services.web_search_service import WebSearchService


logger = logging.getLogger(__name__)


class RepoAnalysis(BaseModel):
    """Result from repository analysis."""

    summary: str = ""
    language: str = ""
    dependencies: List[str] = Field(default_factory=list)
    key_files: Dict[str, str] = Field(default_factory=dict)
    confidence: float = 0.5


class MemoryRetrieval(BaseModel):
    """Result from memory retrieval."""

    similar_plans: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    confidence: float = 0.5


class ConstraintExtraction(BaseModel):
    """Result from constraint extraction."""

    explicit_constraints: List[str] = Field(default_factory=list)
    implicit_constraints: List[str] = Field(default_factory=list)
    technical_requirements: List[str] = Field(default_factory=list)
    confidence: float = 0.5


class WebResearch(BaseModel):
    """Result from web research."""

    findings: List[str] = Field(default_factory=list)
    best_practices: List[str] = Field(default_factory=list)
    tools_and_libraries: List[str] = Field(default_factory=list)
    confidence: float = 0.5


class PlanBrief(BaseModel):
    """Synthesized plan brief from all context sources."""

    user_intent: str
    repo_analysis: Optional[RepoAnalysis] = None
    memory_retrieval: Optional[MemoryRetrieval] = None
    constraint_extraction: Optional[ConstraintExtraction] = None
    web_research: Optional[WebResearch] = None
    synthesized_context: str = ""
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    synthesized_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RepoAnalyser:
    """Analyzes GitHub repositories for context."""

    def __init__(self, llm_gateway: LLMGateway, github_token: Optional[str] = None):
        self.llm = llm_gateway
        self.github_analyzer = GitHubAnalyzer(github_token or "")

    async def analyze(self, context: ExternalContext) -> RepoAnalysis:
        """Analyze a GitHub repository."""
        try:
            if context.source_type != "github":
                return RepoAnalysis(confidence=0.0)

            repo_url = context.source_url
            if not repo_url:
                return RepoAnalysis(confidence=0.0)

            result = await self.github_analyzer.analyze_repository(repo_url)

            return RepoAnalysis(
                summary=result.get("content_summary", ""),
                language=result.get("metadata", {}).get("language", ""),
                dependencies=list(result.get("dependencies", {}).get("python", []))
                + list(result.get("dependencies", {}).get("javascript", [])),
                key_files=result.get("key_files", {}),
                confidence=0.8,
            )

        except Exception as e:
            logger.warning(f"Repo analysis failed: {e}")
            return RepoAnalysis(confidence=0.0)


class MemoryRetriever:
    """Retrieves similar plans from memory."""

    def __init__(self, memory_layer: MemoryLayer):
        self.memory = memory_layer

    async def retrieve(self, user_intent: str, limit: int = 5) -> MemoryRetrieval:
        """Retrieve similar plans from memory."""
        try:
            query = MemorySearchQuery(
                query=user_intent,
                limit=limit,
                similarity_threshold=0.6,
            )

            results = await self.memory.search_similar_plans(query)

            insights = []
            for result in results:
                if result.similarity_score > 0.7:
                    insights.append(f"Similar plan: {result.user_intent} (similarity: {result.similarity_score:.2f})")

            return MemoryRetrieval(
                similar_plans=[r.model_dump(mode="json") for r in results],
                insights=insights,
                confidence=0.7 if results else 0.3,
            )

        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
            return MemoryRetrieval(confidence=0.0)


class ConstraintExtractor:
    """Extracts constraints from user intent and context."""

    def __init__(self, llm_gateway: LLMGateway):
        self.llm = llm_gateway

    async def extract(
        self,
        user_intent: str,
        plan: Plan,
    ) -> ConstraintExtraction:
        """Extract constraints using LLM analysis."""
        try:
            # Simple keyword-based extraction for now
            explicit_constraints: List[str] = []
            implicit_constraints: List[str] = []
            technical_requirements: List[str] = []

            # Extract explicit constraints
            constraint_keywords = ["must", "should", "require", "need", "constraint"]
            words = user_intent.lower().split()
            for keyword in constraint_keywords:
                if keyword in words:
                    explicit_constraints.append(f"Contains '{keyword}' - indicates constraint")

            # Extract technical requirements
            tech_keywords = {
                "api": "REST API implementation",
                "database": "Database integration",
                "auth": "Authentication system",
                "test": "Testing framework",
                "deploy": "Deployment configuration",
            }

            for keyword, requirement in tech_keywords.items():
                if keyword in user_intent.lower():
                    technical_requirements.append(requirement)

            return ConstraintExtraction(
                explicit_constraints=explicit_constraints,
                implicit_constraints=implicit_constraints,
                technical_requirements=technical_requirements,
                confidence=0.6,
            )

        except Exception as e:
            logger.warning(f"Constraint extraction failed: {e}")
            return ConstraintExtraction(confidence=0.0)


class WebResearcher:
    """Performs web research for planning context."""

    def __init__(self, llm_gateway: LLMGateway, tavily_api_key: Optional[str] = None):
        self.llm = llm_gateway
        self.web_search = WebSearchService(tavily_api_key) if tavily_api_key else None

    async def research(self, user_intent: str) -> WebResearch:
        """Perform web research on the planning topic."""
        try:
            if not self.web_search:
                return WebResearch(confidence=0.0)

            # Generate search query from intent
            search_query = self._generate_search_query(user_intent)

            result = await self.web_search.search(search_query, max_results=5)

            findings = [f"Found: {r.get('title', '')}" for r in result.get("results", [])]
            best_practices = [f"Best practice: {r.get('title', '')}" for r in result.get("results", [])[:3]]

            return WebResearch(
                findings=findings,
                best_practices=best_practices,
                tools_and_libraries=[],
                confidence=0.7 if findings else 0.3,
            )

        except Exception as e:
            logger.warning(f"Web research failed: {e}")
            return WebResearch(confidence=0.0)

    def _generate_search_query(self, user_intent: str) -> str:
        """Generate search query from user intent."""
        # Extract key terms
        words = user_intent.split()
        # Take first few meaningful words
        key_terms = [w for w in words if len(w) > 3][:5]
        return " ".join(key_terms) + " best practices"


class ContextSynthesizer:
    """
    Synthesizes context from multiple parallel specialist agents.

    Runs RepoAnalyser, MemoryRetriever, ConstraintExtractor, and WebResearcher
    in parallel, then synthesizes their outputs into a unified plan brief.
    """

    def __init__(self, llm_gateway: LLMGateway, memory_layer: MemoryLayer):
        """
        Initialize context synthesizer.

        Args:
            llm_gateway: LLM gateway for analysis
            memory_layer: Memory layer for retrieving similar plans
        """
        self.llm = llm_gateway
        self.memory = memory_layer

        # Initialize specialist agents
        self.repo_analyser = RepoAnalyser(llm_gateway)
        self.memory_retriever = MemoryRetriever(memory_layer)
        self.constraint_extractor = ConstraintExtractor(llm_gateway)
        self.web_researcher = WebResearcher(llm_gateway)

    async def synthesize(
        self,
        plan: Plan,
        external_contexts: List[ExternalContext],
    ) -> PlanBrief:
        """
        Synthesize context from all specialist agents in parallel.

        Args:
            plan: The current planning session
            external_contexts: List of external context sources

        Returns:
            PlanBrief with synthesized context
        """
        # Prepare parallel tasks
        tasks: List[Any] = []

        # Repo analysis task (if GitHub context provided)
        github_contexts = [c for c in external_contexts if c.source_type == "github"]
        if github_contexts:
            tasks.append(self._analyze_repos_safe(github_contexts[0]))

        # Memory retrieval task
        tasks.append(self._retrieve_memory_safe(plan.user_intent))

        # Constraint extraction task
        tasks.append(self._extract_constraints_safe(plan.user_intent, plan))

        # Web research task
        tasks.append(self._web_research_safe(plan.user_intent))

        # Run all tasks in parallel with graceful degradation
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        repo_analysis: Optional[RepoAnalysis] = None
        memory_retrieval: Optional[MemoryRetrieval] = None
        constraint_extraction: Optional[ConstraintExtraction] = None
        web_research: Optional[WebResearch] = None

        result_index = 0
        if github_contexts:
            repo_result = results[result_index]
            if not isinstance(repo_result, Exception):
                repo_analysis = repo_result  # type: ignore[assignment]
            result_index += 1

        memory_result = results[result_index]
        if not isinstance(memory_result, Exception):
            memory_retrieval = memory_result  # type: ignore[assignment]
        result_index += 1

        constraint_result = results[result_index]
        if not isinstance(constraint_result, Exception):
            constraint_extraction = constraint_result  # type: ignore[assignment]
        result_index += 1

        web_result = results[result_index]
        if not isinstance(web_result, Exception):
            web_research = web_result  # type: ignore[assignment]

        # Build confidence scores
        confidence_scores = {
            "repo_analysis": repo_analysis.confidence if repo_analysis else 0.0,
            "memory_retrieval": memory_retrieval.confidence if memory_retrieval else 0.0,
            "constraint_extraction": constraint_extraction.confidence if constraint_extraction else 0.0,
            "web_research": web_research.confidence if web_research else 0.0,
        }

        # Synthesize context
        synthesized_context = self._build_synthesized_context(
            repo_analysis,
            memory_retrieval,
            constraint_extraction,
            web_research,
        )

        brief = PlanBrief(
            user_intent=plan.user_intent,
            repo_analysis=repo_analysis,
            memory_retrieval=memory_retrieval,
            constraint_extraction=constraint_extraction,
            web_research=web_research,
            synthesized_context=synthesized_context,
            confidence_scores=confidence_scores,
        )

        logger.info(
            f"Context synthesis complete: "
            f"{len([s for s in confidence_scores.values() if s > 0.5])} "
            f"high-confidence sources"
        )

        return brief

    async def _analyze_repos_safe(self, context: ExternalContext) -> RepoAnalysis:
        """Safe wrapper for repo analysis."""
        return await self.repo_analyser.analyze(context)

    async def _retrieve_memory_safe(self, user_intent: str) -> MemoryRetrieval:
        """Safe wrapper for memory retrieval."""
        return await self.memory_retriever.retrieve(user_intent)

    async def _extract_constraints_safe(
        self,
        user_intent: str,
        plan: Plan,
    ) -> ConstraintExtraction:
        """Safe wrapper for constraint extraction."""
        return await self.constraint_extractor.extract(user_intent, plan)

    async def _web_research_safe(self, user_intent: str) -> WebResearch:
        """Safe wrapper for web research."""
        return await self.web_researcher.research(user_intent)

    def _build_synthesized_context(
        self,
        repo_analysis: Optional[RepoAnalysis],
        memory_retrieval: Optional[MemoryRetrieval],
        constraint_extraction: Optional[ConstraintExtraction],
        web_research: Optional[WebResearch],
    ) -> str:
        """Build synthesized context string from all sources."""
        sections = []

        if repo_analysis and repo_analysis.confidence > 0.5:
            sections.append(f"## Repository Context\n{repo_analysis.summary}")

        if memory_retrieval and memory_retrieval.confidence > 0.5:
            sections.append("## Similar Plans\n" + "\n".join(memory_retrieval.insights[:3]))

        if constraint_extraction and constraint_extraction.confidence > 0.5:
            sections.append("## Requirements\n" + "\n".join(constraint_extraction.technical_requirements))

        if web_research and web_research.confidence > 0.5:
            sections.append("## Best Practices\n" + "\n".join(web_research.best_practices[:3]))

        return "\n\n".join(sections) if sections else "No additional context available."
