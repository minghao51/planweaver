"""Context service for managing external context sources"""
from typing import Optional
from ..models.plan import ExternalContext
from ..config import Settings
from ..services.llm_gateway import LLMGateway


class ContextService:
    """Unified service for processing external context sources"""

    def __init__(self, config: Settings, llm_gateway: LLMGateway):
        self.config = config
        self.llm = llm_gateway

    async def add_github_context(self, repo_url: str) -> ExternalContext:
        """Add GitHub repository context"""
        # Implementation in Task 5
        raise NotImplementedError("GitHub context not yet implemented")

    async def add_web_search_context(self, query: str) -> ExternalContext:
        """Add web search context"""
        # Implementation in Task 6
        raise NotImplementedError("Web search not yet implemented")

    async def add_file_context(self, filename: str, content: bytes) -> ExternalContext:
        """Add uploaded file context"""
        # Implementation in Task 7
        raise NotImplementedError("File processing not yet implemented")
