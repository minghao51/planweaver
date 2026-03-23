"""
PlanWeaver Negotiator

LLM-powered intent classification and plan mutation for the universal
message endpoint. Replaces the binary approve/reject flow with structured
negotiation.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from .models.session import (
    NegotiatorIntent,
    NegotiatorOutput,
    PlanMutation,
    PlanMutationType,
    SessionState,
)
from .models.plan import (
    Plan,
    ExecutionStep,
)
from .services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)


class Negotiator:
    """
    Classifies user intent and produces plan mutations.

    The Negotiator is the interface between free-form user messages
    and structured plan operations. It:
    1. Classifies the user's intent
    2. Extracts any mutations needed
    3. Generates a contextual response
    4. Determines if state transition is needed
    """

    SYSTEM_PROMPT = """You are a planning assistant called the Negotiator. Your role is to classify user messages and produce structured plan mutations.

Available intents:
- approve: User wants to approve the current plan/candidate for execution
- reject: User wants to reject and cancel
- revise: User wants to make changes to the plan
- ask_question: User is asking a clarifying question
- answer: User is providing an answer to a clarifying question
- execute: User wants to start/continue execution
- cancel: User wants to cancel the session
- provide_context: User is adding external context (GitHub, web search, file)
- status_query: User is asking about the current state

For each message, output a JSON object with:
{
  "intent": "intent_name",
  "response_message": "Natural language response to the user",
  "mutations": [
    {
      "mutation_type": "type_of_change",
      "step_id": null,
      "key": "constraint_key",
      "value": "new_value"
    }
  ],
  "state_transition": "next_state_if_needed",
  "clarification_questions": [],
  "confidence": 0.95
}

Rules:
- If intent is "revise", include specific mutations describing what to change
- If there are open questions and user is NOT answering them, ask them first
- Be concise in response_message - 1-2 sentences max
- confidence reflects how certain you are (0.0-1.0)
- If intent is unclear, ask for clarification rather than guessing
"""

    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or LLMGateway()

    async def process(
        self,
        message: str,
        plan: Plan,
        session_state: SessionState,
        message_history: Optional[List[Dict[str, Any]]] = None,
    ) -> NegotiatorOutput:
        """
        Process a user message and produce a NegotiatorOutput.

        Args:
            message: The user's message
            plan: Current plan state
            session_state: Current session state
            message_history: Previous messages for context

        Returns:
            NegotiatorOutput with classified intent, mutations, and response
        """
        context = self._build_context(plan, session_state, message_history)
        full_prompt = f"""{self.SYSTEM_PROMPT}

{context}

User message: {message}
"""

        try:
            response = self.llm.complete(
                model="gemini-2.5-flash",
                messages=[{"role": "user", "content": full_prompt}],
                response_format=NegotiatorOutput,
            )
            return NegotiatorOutput.model_validate_json(response["content"])

        except Exception as e:
            logger.error(f"Negotiator error: {e}")
            return self._fallback_output(message, plan)

    def _build_context(
        self,
        plan: Plan,
        session_state: SessionState,
        message_history: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Build context string for the LLM."""
        lines = [
            f"Session State: {session_state.value}",
            f"Plan Status: {plan.status.value}",
            f"User Intent: {plan.user_intent}",
            "",
        ]

        if plan.locked_constraints:
            lines.append("Locked Constraints:")
            for k, v in plan.locked_constraints.items():
                lines.append(f"  - {k}: {v}")
            lines.append("")

        if plan.open_questions:
            lines.append("Open Questions:")
            for q in plan.open_questions:
                if not q.answered:
                    lines.append(f"  - {q.question}")
            lines.append("")

        if plan.candidate_plans:
            lines.append(f"Candidates ({len(plan.candidate_plans)}):")
            for c in plan.candidate_plans[:3]:
                lines.append(f"  - {c.title} ({c.status.value})")
            lines.append("")

        if plan.execution_graph:
            lines.append(f"Execution Steps ({len(plan.execution_graph)}):")
            for step in plan.execution_graph[:5]:
                lines.append(f"  {step.step_id}. {step.task[:60]}...")
            lines.append("")

        if message_history:
            lines.append("Recent Conversation:")
            for msg in message_history[-4:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")[:100]
                lines.append(f"  {role}: {content}...")
            lines.append("")

        return "\n".join(lines)

    def _fallback_output(self, message: str, plan: Plan) -> NegotiatorOutput:
        """Fallback output when LLM fails."""
        msg_lower = message.lower().strip()

        if any(word in msg_lower for word in ["approve", "yes", "go", "execute", "do it"]):
            intent = NegotiatorIntent.APPROVE
        elif any(word in msg_lower for word in ["reject", "no", "cancel", "stop"]):
            intent = NegotiatorIntent.REJECT
        elif any(word in msg_lower for word in ["?", "how", "what", "why", "when"]):
            intent = NegotiatorIntent.ASK_QUESTION
        elif msg_lower.startswith("add ") or msg_lower.startswith("attach "):
            intent = NegotiatorIntent.PROVIDE_CONTEXT
        else:
            intent = NegotiatorIntent.REVISE

        return NegotiatorOutput(
            intent=intent,
            response_message="I've noted your feedback. What would you like to change?",
            mutations=[],
            clarification_questions=[],
            confidence=0.3,
        )

    def apply_mutations(
        self,
        mutations: List[PlanMutation],
        plan: Plan,
    ) -> Plan:
        """
        Apply negotiated mutations to a plan.

        This is a separate method so mutations can be validated
        and applied atomically.
        """
        for mutation in mutations:
            self._apply_mutation(mutation, plan)
        plan.updated_at = datetime.now(timezone.utc)
        return plan

    def _apply_mutation(self, mutation: PlanMutation, plan: Plan) -> None:
        """Apply a single mutation to the plan."""
        if mutation.mutation_type == PlanMutationType.LOCK_CONSTRAINT:
            if mutation.key:
                plan.lock_constraint(mutation.key, mutation.value)
        elif mutation.mutation_type == PlanMutationType.UNLOCK_CONSTRAINT:
            if mutation.key in plan.locked_constraints:
                del plan.locked_constraints[mutation.key]
        elif mutation.mutation_type == PlanMutationType.ANSWER_QUESTION:
            self._answer_question(plan, mutation)
        elif mutation.mutation_type == PlanMutationType.ADD_STEP:
            self._add_step(plan, mutation)
        elif mutation.mutation_type == PlanMutationType.EDIT_STEP:
            self._edit_step(plan, mutation)
        elif mutation.mutation_type == PlanMutationType.DELETE_STEP:
            self._delete_step(plan, mutation)

    def _answer_question(self, plan: Plan, mutation: PlanMutation) -> None:
        """Answer an open question on the plan."""
        for q in plan.open_questions:
            if not q.answered and mutation.key and mutation.key in q.question.lower():
                q.answer = mutation.value
                q.answered = True
                plan.lock_constraint(q.id, mutation.value)

    def _add_step(self, plan: Plan, mutation: PlanMutation) -> None:
        """Add a new execution step."""
        if not mutation.value:
            return
        next_id = max((s.step_id for s in plan.execution_graph), default=0) + 1
        new_step = ExecutionStep(
            step_id=next_id,
            task=mutation.value,
            prompt_template_id="default",
            assigned_model="gemini-2.5-flash",
            dependencies=[mutation.step_id] if mutation.step_id else [],
        )
        plan.execution_graph.append(new_step)

    def _edit_step(self, plan: Plan, mutation: PlanMutation) -> None:
        """Edit an existing step."""
        if mutation.step_id is None:
            return
        for step in plan.execution_graph:
            if step.step_id == mutation.step_id and mutation.value:
                step.task = mutation.value

    def _delete_step(self, plan: Plan, mutation: PlanMutation) -> None:
        """Delete a step and update dependencies."""
        if mutation.step_id is None:
            return
        plan.execution_graph = [s for s in plan.execution_graph if s.step_id != mutation.step_id]
        for step in plan.execution_graph:
            step.dependencies = [d for d in step.dependencies if d != mutation.step_id]
