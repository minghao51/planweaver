"""Debate planning service (Pattern 7)"""

from __future__ import annotations

from typing import List
import logging

from .llm_gateway import LLMGateway
from ..models.coordination import DebateRound
from ..models.plan import Plan

logger = logging.getLogger(__name__)


class DebateService:
    """Proposer vs Opposer debate with Synthesizer decision (Pattern 7)"""

    def __init__(self, llm_gateway: LLMGateway):
        self.llm = llm_gateway

    def detect_decision_points(self, plan: Plan) -> List[str]:
        """Detect high-stakes decision points from execution graph"""
        decision_points = []
        keywords = [
            "choose between",
            "decide whether",
            "select approach",
            "alternative",
            "option",
            "consider using",
            "evaluate",
        ]

        for step in plan.execution_graph:
            task_lower = step.task.lower()
            if any(kw in task_lower for kw in keywords):
                decision_points.append(step.task)

        return decision_points

    async def conduct_debate_round(
        self,
        decision_point: str,
        plan: Plan,
        proposer_model: str = "claude-3.5-sonnet",
        opposer_model: str = "gpt-4o",
        synthesizer_model: str = "deepseek-chat",
    ) -> DebateRound:
        """Proposer vs Opposer arguments, Synthesizer selects"""

        # 1. Proposer generates argument for approach A
        proposer_prompt = f"""You are the PROPOSER. Argue FOR this approach:

Decision: {decision_point}
Current Plan: {plan.user_intent}

Provide a strong argument supporting this decision. Focus on:
- Benefits and advantages
- Why this approach is optimal
- Expected positive outcomes

Keep your response concise and focused."""

        proposer_response = await self.llm.acomplete(
            model=proposer_model,
            messages=[{"role": "user", "content": proposer_prompt}],
            max_tokens=1024,
        )
        proposer_arg = proposer_response.get("content", "")

        # 2. Opposer generates argument against approach A
        opposer_prompt = f"""You are the OPPOSER. Argue AGAINST this approach:

Decision: {decision_point}
Current Plan: {plan.user_intent}

Provide a strong argument identifying:
- Risks and downsides
- Alternative approaches
- Potential failure modes

Keep your response concise and focused."""

        opposer_response = await self.llm.acomplete(
            model=opposer_model,
            messages=[{"role": "user", "content": opposer_prompt}],
            max_tokens=1024,
        )
        opposer_arg = opposer_response.get("content", "")

        # 3. Synthesizer evaluates and decides
        synthesizer_prompt = f"""You are the SYNTHESIZER. Evaluate these arguments:

PROPOSER (for):
{proposer_arg}

OPPOSER (against):
{opposer_arg}

Decision: {decision_point}

Analyze both arguments and:
1. Select the best approach (proposer or opposer)
2. Explain your reasoning
3. Provide a clear rationale for your decision

Respond in this format:
Selected: [proposer/opposer]
Rationale: [your reasoning]"""

        synthesis_response = await self.llm.acomplete(
            model=synthesizer_model,
            messages=[{"role": "user", "content": synthesizer_prompt}],
            max_tokens=1024,
        )
        synthesis = synthesis_response.get("content", "")

        # Parse the selected approach from synthesis
        selected_approach = self._parse_selected_approach(synthesis)

        return DebateRound(
            round_id=str(id(decision_point)),
            decision_point=decision_point,
            proposer_argument=proposer_arg,
            opposer_argument=opposer_arg,
            synthesizer_decision=synthesis,
            selected_approach=selected_approach,
            rationale=synthesis[:500],  # First 500 chars as rationale
        )

    def _parse_selected_approach(self, synthesis: str) -> str:
        """Parse the selected approach from synthesizer response"""
        synthesis_lower = synthesis.lower()

        # Look for explicit selection
        if "selected: proposer" in synthesis_lower or "select: proposer" in synthesis_lower:
            return "proposer"
        elif "selected: opposer" in synthesis_lower or "select: opposer" in synthesis_lower:
            return "opposer"

        # Fallback: look for keywords
        proposer_words = ["support", "favor", "agree with proposer", "proposer is correct"]
        opposer_words = ["agree with opposer", "opposer is correct", "opposer makes sense"]

        proposer_score = sum(1 for word in proposer_words if word in synthesis_lower)
        opposer_score = sum(1 for word in opposer_words if word in synthesis_lower)

        if proposer_score > opposer_score:
            return "proposer"
        elif opposer_score > proposer_score:
            return "opposer"

        # Default to proposer if unclear
        return "proposer"
