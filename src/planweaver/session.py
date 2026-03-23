"""
PlanWeaver Session State Machine

Manages state transitions for planning sessions with event-driven architecture.
Validates transitions and emits events for auditing.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Callable
import logging

from .models.session import (
    SessionState,
    StateTransitionEvent,
    ConvergenceStatus,
    NegotiatorIntent,
)

logger = logging.getLogger(__name__)


VALID_TRANSITIONS: Dict[SessionState, Dict[str, SessionState]] = {
    SessionState.GOAL_RECEIVED: {
        "start_clarifying": SessionState.CLARIFYING,
        "start_planning": SessionState.PLANNING,
        "cancel": SessionState.DONE,
    },
    SessionState.CLARIFYING: {
        "all_questions_answered": SessionState.PLANNING,
        "cancel": SessionState.DONE,
    },
    SessionState.PLANNING: {
        "plan_ready": SessionState.NEGOTIATING,
        "need_clarification": SessionState.CLARIFYING,
        "cancel": SessionState.DONE,
    },
    SessionState.NEGOTIATING: {
        "approve": SessionState.EXECUTING,
        "request_revision": SessionState.PLANNING,
        "cancel": SessionState.DONE,
    },
    SessionState.EXECUTING: {
        "execution_complete": SessionState.DONE,
        "execution_failed": SessionState.DONE,
    },
    SessionState.DONE: {},
}


class SessionStateMachine:
    """
    Manages session state transitions with validation and event emission.

    Attributes:
        session_id: The session this state machine manages
        current_state: Current session state
        transition_history: List of all transitions for audit trail
        convergence_tracker: Tracks convergence for negotiation
    """

    def __init__(self, session_id: str, initial_state: SessionState = SessionState.GOAL_RECEIVED):
        self.session_id = session_id
        self.current_state = initial_state
        self.transition_history: List[StateTransitionEvent] = []
        self._convergence_rounds = 0
        self._last_mutation_round = 0
        self._event_handlers: Dict[str, List[Callable]] = {}

    def can_transition(self, event: str) -> bool:
        """Check if a given event can trigger a valid transition from current state."""
        return event in VALID_TRANSITIONS.get(self.current_state, {})

    def get_next_state(self, event: str) -> Optional[SessionState]:
        """Get the next state for a given event, or None if invalid."""
        return VALID_TRANSITIONS.get(self.current_state, {}).get(event)

    def transition(self, event: str, context: Optional[Dict[str, Any]] = None) -> SessionState:
        """
        Attempt to transition to a new state via the given event.

        Args:
            event: The event name triggering the transition
            context: Optional context dict for the transition event

        Returns:
            The new state

        Raises:
            InvalidTransitionError: If the event is not valid from current state
        """
        if context is None:
            context = {}

        next_state = self.get_next_state(event)

        if next_state is None:
            raise InvalidTransitionError(f"Invalid transition: event '{event}' from state '{self.current_state.value}'")

        previous_state = self.current_state
        self.current_state = next_state

        transition_event = StateTransitionEvent(
            session_id=self.session_id,
            from_state=previous_state,
            to_state=next_state,
            event=event,
            context=context,
        )
        self.transition_history.append(transition_event)

        logger.info(f"Session {self.session_id}: {previous_state.value} -> {next_state.value} (via {event})")

        self._emit_event(event, transition_event)

        if next_state == SessionState.NEGOTIATING:
            self._convergence_rounds = 0

        return next_state

    def record_negotiation_round(self, had_mutation: bool) -> None:
        """Track negotiation rounds for convergence detection."""
        if had_mutation:
            self._last_mutation_round = self._convergence_rounds
            self._convergence_rounds = 0
        else:
            self._convergence_rounds += 1

    def check_convergence(
        self,
        max_rounds: int = 5,
        min_rounds: int = 2,
        user_intent: Optional[NegotiatorIntent] = None,
    ) -> ConvergenceStatus:
        """
        Determine if negotiation has converged.

        Convergence requires:
        - At least min_rounds without mutations, OR
        - User explicitly approved/rejected, OR
        - max_rounds reached (forced convergence)
        """
        reasons = []
        is_converged = False

        if user_intent == NegotiatorIntent.APPROVE:
            is_converged = True
            reasons.append("User explicitly approved the plan")
        elif user_intent == NegotiatorIntent.REJECT:
            is_converged = True
            reasons.append("User explicitly rejected the plan")
        elif self._convergence_rounds >= max_rounds:
            is_converged = True
            reasons.append(f"Max rounds ({max_rounds}) reached")
        elif self._convergence_rounds >= min_rounds:
            is_converged = True
            reasons.append(f"Converged after {self._convergence_rounds} quiet rounds")

        return ConvergenceStatus(
            is_converged=is_converged,
            rounds_without_change=self._convergence_rounds,
            last_mutation_round=self._last_mutation_round,
            reasons=reasons,
        )

    def on(self, event: str, handler: Callable[[StateTransitionEvent], None]) -> None:
        """Register an event handler for a transition event."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _emit_event(self, event: str, transition_event: StateTransitionEvent) -> None:
        """Emit all registered handlers for an event."""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(transition_event)
            except Exception as e:
                logger.error(f"Error in event handler for {event}: {e}")

    def get_state(self) -> SessionState:
        """Get the current state."""
        return self.current_state

    def get_history(self) -> List[StateTransitionEvent]:
        """Get the full transition history."""
        return list(self.transition_history)


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    pass
