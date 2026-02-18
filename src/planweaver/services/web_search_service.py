"""Web search service for planning context"""
from tavily import TavilyClient
from typing import Dict, Any, List


class WebSearchService:
    """Web search using Tavily API"""

    def __init__(self, api_key: str):
        self.client = TavilyClient(api_key=api_key)

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Execute web search and return results"""
        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
                include_answer=True,
                include_raw_content=False
            )

            # Extract results
            results = response.get("results", [])

            # Build formatted results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("content", "")[:500]
                })

            # Get AI answer if available
            answer = response.get("answer", "")

            # Build summary
            summary = self._build_summary(query, formatted_results, answer)

            return {
                "query": query,
                "results": formatted_results,
                "answer": answer,
                "summary": summary
            }

        except Exception as e:
            raise ValueError(f"Web search failed: {str(e)}")

    def _build_summary(
        self,
        query: str,
        results: List[Dict[str, str]],
        answer: str
    ) -> str:
        """Build search summary for planner"""
        summary = f"## Web Search Results for: {query}\n\n"

        if answer:
            summary += f"**AI Answer:** {answer}\n\n"

        summary += "### Top Results:\n\n"
        for i, result in enumerate(results[:5], 1):
            summary += f"{i}. **{result['title']}**\n"
            summary += f"   {result['snippet']}\n"
            summary += f"   URL: {result['url']}\n\n"

        return summary
