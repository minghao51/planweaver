from typing import List, Dict, Any, Literal
from logging import getLogger
from .llm_gateway import LLMGateway

logger = getLogger(__name__)


class VariantGenerator:
    """Generates optimized variants of selected proposals"""

    def __init__(self):
        self.llm_gateway = LLMGateway()

    def generate_variant(
        self,
        proposal: Dict[str, Any],
        variant_type: Literal["simplified", "enhanced", "cost-optimized"],
        user_context: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a single variant of a proposal

        Args:
            proposal: The original proposal with execution graph
            variant_type: Type of optimization to apply
            user_context: Additional context from user

        Returns:
            Dict with variant data including execution_graph and metadata
        """
        logger.info(f"Generating {variant_type} variant for proposal")

        system_prompt = self._get_system_prompt(variant_type)
        user_prompt = self._build_user_prompt(proposal, variant_type, user_context)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self.llm_gateway.complete(
            model="claude-3.5-sonnet",
            messages=messages,
            json_mode=True,
            max_tokens=4096
        )

        try:
            import json
            variant_data = json.loads(response["content"])
            logger.info(f"Successfully generated {variant_type} variant")
            return variant_data
        except Exception as e:
            logger.error(f"Failed to parse variant response: {e}")
            raise

    def _get_system_prompt(self, variant_type: str) -> str:
        """Get system prompt based on variant type"""
        prompts = {
            "simplified": """You are a planning optimization expert. Your task is to create a SIMPLIFIED version of a plan that:
1. Reduces the number of steps without losing core functionality
2. Combines related steps where possible
3. Removes non-essential intermediate steps
4. Maintains feasibility and correctness

Return a JSON object with:
- execution_graph: optimized execution steps
- metadata: {step_count, complexity_score, optimization_notes, estimated_time_minutes, estimated_cost_usd}""",
            "enhanced": """You are a planning optimization expert. Your task is to create an ENHANCED version of a plan that:
1. Adds more robust error handling and validation steps
2. Includes additional quality checks and testing
3. Improves reliability and success rate
4. May increase steps but provides better outcomes

Return a JSON object with:
- execution_graph: optimized execution steps
- metadata: {step_count, complexity_score, optimization_notes, estimated_time_minutes, estimated_cost_usd}""",
            "cost-optimized": """You are a planning optimization expert. Your task is to create a COST-OPTIMIZED version of a plan that:
1. Reduces API costs by using cheaper models where possible
2. Minimizes token usage and API calls
3. Optimizes for free/low-cost models
4. Maintains acceptable quality standards

Return a JSON object with:
- execution_graph: optimized execution steps
- metadata: {step_count, complexity_score, optimization_notes, estimated_time_minutes, estimated_cost_usd}"""
        }
        return prompts.get(variant_type, prompts["simplified"])

    def _build_user_prompt(
        self,
        proposal: Dict[str, Any],
        variant_type: str,
        user_context: str
    ) -> str:
        """Build the user prompt for variant generation"""
        prompt = f"""Generate a {variant_type} variant of this plan:

**Title:** {proposal.get('title', 'N/A')}

**Description:** {proposal.get('description', 'N/A')}

**Execution Graph:**
{self._format_execution_graph(proposal.get('execution_graph', []))}"""

        if user_context:
            prompt += f"\n\n**Additional Context:**\n{user_context}"

        prompt += "\n\nRespond ONLY with a valid JSON object containing the optimized execution_graph and metadata."

        return prompt

    def _format_execution_graph(self, graph: List[Dict]) -> str:
        """Format execution graph for prompt"""
        if not graph:
            return "No execution steps provided."

        formatted = []
        for step in graph:
            formatted.append(
                f"Step {step.get('step_id', '?')}: {step.get('task', 'Unknown task')}\n"
                f"  Model: {step.get('assigned_model', 'N/A')}\n"
                f"  Status: {step.get('status', 'PENDING')}"
            )
        return "\n".join(formatted)
