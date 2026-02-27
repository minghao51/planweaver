from typing import List, Dict, Any, Literal
from logging import getLogger
from .llm_gateway import LLMGateway

logger = getLogger(__name__)


class ModelRater:
    """Rates plans using multiple AI models for comparison"""

    # Default models to use for rating
    DEFAULT_MODELS = ["claude-3.5-sonnet", "gpt-4o", "deepseek-chat"]

    # Rating criteria
    CRITERIA = ["feasibility", "cost_efficiency", "time_efficiency", "complexity", "risk_level"]

    def __init__(self):
        self.llm_gateway = LLMGateway()

    def rate_plan(
        self,
        plan: Dict[str, Any],
        models: List[str] | None = None,
        criteria: List[str] | None = None
    ) -> Dict[str, Any]:
        """
        Rate a plan using multiple AI models

        Args:
            plan: Plan to rate (with execution_graph)
            models: List of model names to use (default: DEFAULT_MODELS)
            criteria: List of criteria to rate (default: CRITERIA)

        Returns:
            Dict with model_name -> rating mapping
        """
        models = models or self.DEFAULT_MODELS
        criteria = criteria or self.CRITERIA

        logger.info(f"Rating plan with {len(models)} models on {len(criteria)} criteria")

        ratings = {}
        for model in models:
            try:
                model_rating = self._rate_with_model(plan, model, criteria)
                ratings[model] = model_rating
                logger.info(f"Got rating from {model}")
            except Exception as e:
                logger.error(f"Failed to get rating from {model}: {e}")
                ratings[model] = self._get_error_rating(str(e))

        return ratings

    def _rate_with_model(
        self,
        plan: Dict[str, Any],
        model: str,
        criteria: List[str]
    ) -> Dict[str, Any]:
        """Rate plan using a specific model"""
        system_prompt = self._get_rating_system_prompt(criteria)
        user_prompt = self._build_rating_prompt(plan, criteria)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self.llm_gateway.complete(
            model=model,
            messages=messages,
            json_mode=True,
            max_tokens=2048
        )

        try:
            import json
            rating_data = json.loads(response["content"])

            # Calculate overall score
            ratings = rating_data.get("ratings", {})
            overall = sum(ratings.values()) / len(ratings) if ratings else 5.0

            return {
                "model_name": model,
                "ratings": ratings,
                "overall_score": round(overall, 2),
                "reasoning": rating_data.get("reasoning", "")
            }
        except Exception as e:
            logger.error(f"Failed to parse rating response from {model}: {e}")
            raise

    def _get_rating_system_prompt(self, criteria: List[str]) -> str:
        """Get system prompt for rating"""
        criteria_list = ", ".join(criteria)
        return f"""You are an expert plan evaluator. Your task is to rate plans on the following criteria: {criteria_list}.

For each criterion:
- Provide a score from 1.0 (very poor) to 10.0 (excellent)
- Be objective, consistent, and fair
- Consider real-world constraints and practicality
- 5.0 should represent "average" or "acceptable"

After scoring, provide:
1. Brief reasoning (2-3 sentences) explaining your ratings
2. Any significant concerns or advantages

Return a JSON object with:
{{
  "ratings": {{
    "feasibility": 8.5,
    "cost_efficiency": 7.0,
    "time_efficiency": 9.0,
    "complexity": 6.5,
    "risk_level": 7.5
  }},
  "reasoning": "Brief explanation of the ratings..."
}}"""

    def _build_rating_prompt(self, plan: Dict[str, Any], criteria: List[str]) -> str:
        """Build user prompt for rating"""
        prompt = f"""Rate this plan:

**Title:** {plan.get('title', 'N/A')}

**Description:** {plan.get('description', 'N/A')}

**Execution Steps:** {len(plan.get('execution_graph', []))} steps

**Execution Graph:**
{self._format_execution_graph(plan.get('execution_graph', []))}

**Metadata:**
{self._format_metadata(plan.get('metadata', {}))}

Please rate this plan on: {", ".join(criteria)}.

Respond ONLY with a valid JSON object containing ratings and reasoning."""

        return prompt

    def _format_execution_graph(self, graph: List[Dict]) -> str:
        """Format execution graph for prompt"""
        if not graph:
            return "No execution steps."

        formatted = []
        for step in graph[:10]:  # Limit to first 10 steps
            formatted.append(
                f"- Step {step.get('step_id', '?')}: {step.get('task', 'Unknown')}"
            )

        if len(graph) > 10:
            formatted.append(f"... and {len(graph) - 10} more steps")

        return "\n".join(formatted)

    def _format_metadata(self, metadata: Dict) -> str:
        """Format metadata for prompt"""
        if not metadata:
            return "No metadata available."

        formatted = []
        for key, value in metadata.items():
            formatted.append(f"- {key}: {value}")
        return "\n".join(formatted)

    def _get_error_rating(self, error_msg: str) -> Dict[str, Any]:
        """Return error rating"""
        return {
            "model_name": "error",
            "ratings": {c: 5.0 for c in self.CRITERIA},
            "overall_score": 5.0,
            "reasoning": f"Error during rating: {error_msg}"
        }
