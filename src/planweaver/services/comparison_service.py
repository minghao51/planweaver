"""Service for comparing proposals with detailed execution graphs."""

from typing import Dict, List, Tuple, Literal
import logging
from decimal import Decimal
from cachetools import TTLCache

from planweaver.models.plan import (
    Plan,
    ProposalDetail,
    ProposalComparison,
    StepSummary,
    ExecutionStep
)

logger = logging.getLogger(__name__)

# Cache configuration: max 100 graphs, 10 minute TTL per entry
_CACHE_MAX_SIZE = 100
_CACHE_TTL_SECONDS = 600


class ProposalComparisonService:
    """Service for generating detailed proposal comparisons."""

    def __init__(self, planner, llm_gateway):
        self.planner = planner
        self.llm = llm_gateway
        self._graph_cache: TTLCache[Tuple[str, str], List[ExecutionStep]] = TTLCache(
            maxsize=_CACHE_MAX_SIZE,
            ttl=_CACHE_TTL_SECONDS
        )

    def compare_proposals(
        self,
        plan: Plan,
        proposal_ids: List[str]
    ) -> ProposalComparison:
        """Generate detailed comparison of selected proposals.

        Args:
            plan: The plan containing proposals
            proposal_ids: List of proposal IDs to compare (must be >= 2)

        Returns:
            ProposalComparison with full execution graphs and diff analysis

        Raises:
            ValueError: If fewer than 2 proposals provided
        """
        if len(proposal_ids) < 2:
            raise ValueError(
                f"Comparison requires at least 2 proposals. Got {len(proposal_ids)}"
            )

        # Generate full execution graphs for each proposal
        proposal_details = []
        for prop_id in proposal_ids:
            try:
                graph = self._generate_or_get_execution_graph(plan, prop_id)
                time_est = self._estimate_time(graph)
                cost_est = self._estimate_cost(graph)
                risks = self._extract_risks(graph)

                proposal_details.append(ProposalDetail(
                    proposal_id=prop_id,
                    full_execution_graph=graph,
                    accurate_time_estimate=time_est,
                    accurate_cost_estimate=cost_est,
                    all_risk_factors=risks
                ))
            except Exception as e:
                logger.error(f"Failed to generate details for proposal {prop_id}: {e}")
                # Add partial result with error
                proposal_details.append(ProposalDetail(
                    proposal_id=prop_id,
                    full_execution_graph=[],
                    accurate_time_estimate=0,
                    accurate_cost_estimate=Decimal("0"),
                    all_risk_factors=[],
                    generation_error=str(e)
                ))

        # Compute diff between proposals
        common_steps = self._find_common_steps(proposal_details)
        unique_steps = self._find_unique_steps(proposal_details, common_steps)

        # Build comparison metrics
        time_comparison = {p.proposal_id: p.accurate_time_estimate
                          for p in proposal_details}
        cost_comparison = {p.proposal_id: p.accurate_cost_estimate
                          for p in proposal_details}
        complexity_comparison = {
            p.proposal_id: self._calculate_complexity_score(p)
            for p in proposal_details
        }

        return ProposalComparison(
            session_id=plan.session_id,
            proposals=proposal_details,
            common_steps=common_steps,
            unique_steps_by_proposal=unique_steps,
            time_comparison=time_comparison,
            cost_comparison=cost_comparison,
            complexity_comparison=complexity_comparison
        )

    def _generate_or_get_execution_graph(
        self,
        plan: Plan,
        proposal_id: str
    ) -> List[ExecutionStep]:
        """Generate execution graph or retrieve from cache."""
        cache_key = (plan.session_id, proposal_id)

        # Check cache
        if cache_key in self._graph_cache:
            logger.debug(f"Cache hit for {cache_key}")
            return self._graph_cache[cache_key]

        # Generate graph
        logger.debug(f"Generating execution graph for proposal {proposal_id}")
        proposal = plan.get_proposal_by_id(proposal_id)

        # Use planner's decompose method with proposal context
        constraints = {
            **plan.locked_constraints,
            "selected_approach": proposal.title,
            "approach_description": proposal.description
        }

        graph = self.planner.decompose_into_steps(
            user_intent=plan.user_intent,
            locked_constraints=constraints,
            scenario_name=plan.scenario_name
        )

        # Cache with TTL (automatic expiration handled by TTLCache)
        self._graph_cache[cache_key] = graph
        logger.debug(f"Cached execution graph for {cache_key}")

        return graph

    def _find_common_steps(
        self,
        proposals: List[ProposalDetail]
    ) -> List[StepSummary]:
        """Find steps common to all proposals using fuzzy matching."""
        if not proposals:
            return []

        common = []
        for step in proposals[0].full_execution_graph:
            # Check if similar step exists in all other proposals
            is_common = True
            for prop in proposals[1:]:
                if not self._has_similar_step(step, prop.full_execution_graph):
                    is_common = False
                    break

            if is_common:
                common.append(StepSummary(
                    task=step.task,
                    complexity=self._infer_step_complexity(step),
                    estimated_time_minutes=2  # Default
                ))

        return common

    def _has_similar_step(
        self,
        step: ExecutionStep,
        steps: List[ExecutionStep]
    ) -> bool:
        """Check if a similar step exists in the list."""
        step_lower = step.task.lower()
        step_words = set(step_lower.split())

        for s in steps:
            s_lower = s.task.lower()
            s_words = set(s_lower.split())

            # Direct match
            if s_lower == step_lower:
                return True

            # Fuzzy match (if one contains the other)
            if (len(step_lower) > 5 and
                (step_lower in s_lower or s_lower in step_lower)):
                return True

            # Word overlap match (if they share significant words)
            if step_words and s_words:
                overlap = step_words & s_words
                # If more than half the words overlap (min 2 words), consider similar
                min_words = min(len(step_words), len(s_words))
                if len(overlap) >= max(2, min_words * 0.5):
                    return True

        return False

    def _find_unique_steps(
        self,
        proposals: List[ProposalDetail],
        common_steps: List[StepSummary]
    ) -> Dict[str, List[StepSummary]]:
        """Find steps unique to each proposal."""
        common_tasks = {s.task.lower() for s in common_steps}

        unique_by_proposal = {}
        for prop in proposals:
            unique = []
            for step in prop.full_execution_graph:
                if step.task.lower() not in common_tasks:
                    unique.append(StepSummary(
                        task=step.task,
                        complexity=self._infer_step_complexity(step),
                        estimated_time_minutes=2
                    ))
            unique_by_proposal[prop.proposal_id] = unique

        return unique_by_proposal

    def _infer_step_complexity(self, step: ExecutionStep) -> Literal["Low", "Medium", "High"]:
        """Infer complexity from step description."""
        task_lower = step.task.lower()

        # High complexity indicators (use word boundaries or substring matches)
        high_keywords = ["migrat", "deploy", "architecture", "integration", "refactor"]
        if any(kw in task_lower for kw in high_keywords):
            return "High"

        # Low complexity indicators (check these first to be more specific)
        low_keywords = ["install", "configure", "test", "verify", "backup"]
        if any(kw in task_lower for kw in low_keywords):
            return "Low"

        # Medium complexity indicators (like "update" by itself)
        medium_keywords = ["update", "modify", "change"]
        if any(kw in task_lower for kw in medium_keywords):
            return "Medium"

        return "Medium"

    def _calculate_complexity_score(self, prop: ProposalDetail) -> Literal["Low", "Medium", "High"]:
        """Calculate overall complexity score for proposal."""
        if not prop.full_execution_graph:
            return "Medium"

        complexities = [self._infer_step_complexity(s) for s in prop.full_execution_graph]

        high_count = complexities.count("High")
        if high_count >= len(complexities) / 2:
            return "High"

        low_count = complexities.count("Low")
        if low_count >= len(complexities) / 2:
            return "Low"

        return "Medium"

    def _estimate_time(self, steps: List[ExecutionStep]) -> int:
        """Estimate execution time in minutes."""
        base_time_per_step = 2  # minutes
        complexity_multiplier = {"Low": 1.0, "Medium": 1.5, "High": 2.5}

        total = 0
        for step in steps:
            complexity = self._infer_step_complexity(step)
            total += base_time_per_step * complexity_multiplier[complexity]

        return int(total)

    def _estimate_cost(self, steps: List[ExecutionStep]) -> Decimal:
        """Estimate execution cost in USD."""
        if not steps:
            return Decimal("0")

        tokens_per_step = 500

        # Pricing database (prices per 1M tokens)
        pricing = {
            "gemini-2.5-flash": 0.075,
            "gemini-2.5-pro": 0.15,
            "gemini-3-flash": 0.15,
            "gemini-3-pro": 0.25,
            "deepseek/deepseek-chat": 0.14,
            "deepseek-chat": 0.14,
            "claude-3.5-sonnet": 3.0,
            "anthropic/claude-3-5-sonnet-20241022": 3.0,
            "gpt-4o": 2.5,
            "openai/gpt-4o": 2.5,
        }

        model = steps[0].assigned_model if steps else "gemini-2.5-flash"

        # Try exact match
        if model in pricing:
            price_per_m = pricing[model]
        # Try prefix match (e.g., "gemini-" -> 0.15)
        else:
            price_per_m = next(
                (v for k, v in pricing.items() if model.startswith(k) or k.endswith(model)),
                0.15  # Default conservative estimate
            )

        total_tokens = len(steps) * tokens_per_step
        cost = (total_tokens / 1_000_000) * price_per_m

        return Decimal(str(round(cost, 4)))

    def _extract_risks(self, steps: List[ExecutionStep]) -> List[str]:
        """Extract risk factors from execution steps."""
        risks = []

        risk_keywords = {
            "production": "Production changes",
            "delete": "Data deletion risk",
            "migrat": "Data migration risk",
            "external": "External API dependency",
            "third-party": "Third-party service dependency",
        }

        for step in steps:
            task_lower = step.task.lower()
            for keyword, risk in risk_keywords.items():
                if keyword in task_lower and risk not in risks:
                    risks.append(risk)

        return risks[:5]  # Max 5 risks

    def clear_cache(self):
        """Clear all cached execution graphs."""
        self._graph_cache.clear()
        logger.info("Cleared comparison cache")
