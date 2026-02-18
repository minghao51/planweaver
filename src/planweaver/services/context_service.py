"""Context service for managing external context sources"""
from typing import Optional
from ..models.plan import ExternalContext
from ..config import Settings
from ..services.llm_gateway import LLMGateway
from .github_analyzer import GitHubAnalyzer
from .web_search_service import WebSearchService
from .file_processor import FileProcessorService


class ContextService:
    """Unified service for processing external context sources"""

    def __init__(self, config: Settings, llm_gateway: LLMGateway):
        self.config = config
        self.llm = llm_gateway
        self.github_analyzer = GitHubAnalyzer(config.github_token)
        if config.tavily_api_key:
            self.web_search = WebSearchService(config.tavily_api_key)
        else:
            self.web_search = None
        self.file_processor = FileProcessorService(
            max_size_mb=config.max_file_size_mb,
            allowed_types=config.allowed_file_types
        )

    async def add_github_context(self, repo_url: str) -> ExternalContext:
        """Add GitHub repository context"""
        try:
            # Analyze repository
            analysis = await self.github_analyzer.analyze_repository(repo_url)

            # Create ExternalContext
            context = ExternalContext(
                source_type="github",
                source_url=repo_url,
                content_summary=analysis["content_summary"],
                metadata={
                    "repo_name": analysis["metadata"]["name"],
                    "language": analysis["metadata"]["language"],
                    "stars": analysis["metadata"]["stars"],
                    "dependencies": analysis["dependencies"],
                    "file_structure": analysis["file_structure"]
                }
            )

            return context

        except Exception as e:
            raise ValueError(f"Failed to analyze GitHub repository: {str(e)}")

    async def add_web_search_context(self, query: str) -> ExternalContext:
        """Add web search context"""
        if not self.web_search:
            raise ValueError("Web search not configured - missing Tavily API key")

        try:
            # Execute search
            search_results = await self.web_search.search(query)

            # Create ExternalContext
            context = ExternalContext(
                source_type="web_search",
                source_url=f"search:{query}",
                content_summary=search_results["summary"],
                metadata={
                    "query": query,
                    "result_count": len(search_results["results"]),
                    "answer": search_results["answer"]
                }
            )

            return context

        except Exception as e:
            raise ValueError(f"Failed to perform web search: {str(e)}")

    async def add_file_context(self, filename: str, content: bytes) -> ExternalContext:
        """Add uploaded file context"""
        try:
            # Process file
            file_data = await self.file_processor.process_file(filename, content)

            # Create ExternalContext
            context = ExternalContext(
                source_type="file_upload",
                content_summary=file_data["summary"],
                metadata={
                    "filename": file_data["filename"],
                    "file_type": file_data["file_type"],
                    "size_bytes": file_data["size_bytes"],
                    "full_content": file_data["content"]
                }
            )

            return context

        except Exception as e:
            raise ValueError(f"Failed to process file: {str(e)}")
