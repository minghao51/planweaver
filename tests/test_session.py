import pytest
from src.planweaver.session import SessionStateMachine, InvalidTransitionError
from src.planweaver.models.session import SessionState, NegotiatorIntent


class TestSessionStateMachine:
    """Tests for SessionStateMachine."""

    def test_initial_state(self):
        sm = SessionStateMachine("test-123")
        assert sm.get_state() == SessionState.GOAL_RECEIVED

    def test_initial_state_custom(self):
        sm = SessionStateMachine("test-123", SessionState.PLANNING)
        assert sm.get_state() == SessionState.PLANNING

    def test_valid_transition_goal_to_planning(self):
        sm = SessionStateMachine("test-123")
        new_state = sm.transition("start_planning")
        assert new_state == SessionState.PLANNING
        assert sm.get_state() == SessionState.PLANNING

    def test_valid_transition_goal_to_clarifying(self):
        sm = SessionStateMachine("test-123")
        new_state = sm.transition("start_clarifying")
        assert new_state == SessionState.CLARIFYING

    def test_valid_transition_clarifying_to_planning(self):
        sm = SessionStateMachine("test-123", SessionState.CLARIFYING)
        new_state = sm.transition("all_questions_answered")
        assert new_state == SessionState.PLANNING

    def test_valid_transition_to_negotiating(self):
        sm = SessionStateMachine("test-123", SessionState.PLANNING)
        new_state = sm.transition("plan_ready")
        assert new_state == SessionState.NEGOTIATING

    def test_valid_transition_negotiating_to_executing(self):
        sm = SessionStateMachine("test-123", SessionState.NEGOTIATING)
        new_state = sm.transition("approve")
        assert new_state == SessionState.EXECUTING

    def test_valid_transition_negotiating_to_planning(self):
        sm = SessionStateMachine("test-123", SessionState.NEGOTIATING)
        new_state = sm.transition("request_revision")
        assert new_state == SessionState.PLANNING

    def test_valid_transition_executing_to_done(self):
        sm = SessionStateMachine("test-123", SessionState.EXECUTING)
        new_state = sm.transition("execution_complete")
        assert new_state == SessionState.DONE

    def test_valid_transition_executing_to_done_failed(self):
        sm = SessionStateMachine("test-123", SessionState.EXECUTING)
        new_state = sm.transition("execution_failed")
        assert new_state == SessionState.DONE

    def test_invalid_transition_raises_error(self):
        sm = SessionStateMachine("test-123")
        with pytest.raises(InvalidTransitionError):
            sm.transition("approve")

    def test_invalid_transition_from_done(self):
        sm = SessionStateMachine("test-123", SessionState.DONE)
        with pytest.raises(InvalidTransitionError):
            sm.transition("start_planning")

    def test_transition_history_recorded(self):
        sm = SessionStateMachine("test-123")
        sm.transition("start_planning")
        sm.transition("plan_ready")

        history = sm.get_history()
        assert len(history) == 2
        assert history[0].from_state == SessionState.GOAL_RECEIVED
        assert history[0].to_state == SessionState.PLANNING
        assert history[1].from_state == SessionState.PLANNING
        assert history[1].to_state == SessionState.NEGOTIATING

    def test_transition_context_captured(self):
        sm = SessionStateMachine("test-123")
        sm.transition("start_planning", {"user": "test_user"})

        history = sm.get_history()
        assert history[0].context == {"user": "test_user"}

    def test_can_transition_returns_true_for_valid(self):
        sm = SessionStateMachine("test-123")
        assert sm.can_transition("start_planning") is True

    def test_can_transition_returns_false_for_invalid(self):
        sm = SessionStateMachine("test-123")
        assert sm.can_transition("approve") is False

    def test_get_next_state_returns_state_for_valid_event(self):
        sm = SessionStateMachine("test-123")
        assert sm.get_next_state("start_planning") == SessionState.PLANNING

    def test_get_next_state_returns_none_for_invalid_event(self):
        sm = SessionStateMachine("test-123")
        assert sm.get_next_state("approve") is None

    def test_convergence_after_max_rounds(self):
        sm = SessionStateMachine("test-123", SessionState.NEGOTIATING)

        for _ in range(5):
            sm.record_negotiation_round(had_mutation=False)

        convergence = sm.check_convergence(max_rounds=5, min_rounds=2)
        assert convergence.is_converged
        assert "Max rounds" in convergence.reasons[0]
        assert convergence.rounds_without_change == 5

    def test_convergence_after_min_rounds_no_mutation(self):
        sm = SessionStateMachine("test-123", SessionState.NEGOTIATING)

        sm.record_negotiation_round(had_mutation=False)
        sm.record_negotiation_round(had_mutation=False)

        convergence = sm.check_convergence(max_rounds=5, min_rounds=2)
        assert convergence.is_converged
        assert "Converged after" in convergence.reasons[0]

    def test_convergence_on_approval(self):
        sm = SessionStateMachine("test-123", SessionState.NEGOTIATING)
        sm.record_negotiation_round(had_mutation=True)

        convergence = sm.check_convergence(max_rounds=5, user_intent=NegotiatorIntent.APPROVE)
        assert convergence.is_converged
        assert "User explicitly approved" in convergence.reasons[0]

    def test_convergence_on_rejection(self):
        sm = SessionStateMachine("test-123", SessionState.NEGOTIATING)
        sm.record_negotiation_round(had_mutation=True)

        convergence = sm.check_convergence(max_rounds=5, user_intent=NegotiatorIntent.REJECT)
        assert convergence.is_converged
        assert "User explicitly rejected" in convergence.reasons[0]

    def test_convergence_not_converged_under_threshold(self):
        sm = SessionStateMachine("test-123", SessionState.NEGOTIATING)

        sm.record_negotiation_round(had_mutation=False)

        convergence = sm.check_convergence(max_rounds=5, min_rounds=2)
        assert not convergence.is_converged

    def test_mutation_resets_convergence_rounds(self):
        sm = SessionStateMachine("test-123", SessionState.NEGOTIATING)

        sm.record_negotiation_round(had_mutation=False)
        sm.record_negotiation_round(had_mutation=False)
        sm.record_negotiation_round(had_mutation=True)
        sm.record_negotiation_round(had_mutation=False)

        assert sm._convergence_rounds == 1

    def test_event_handler_called_on_transition(self):
        sm = SessionStateMachine("test-123")
        called = []

        def handler(event):
            called.append(event.event)

        sm.on("start_planning", handler)
        sm.transition("start_planning")

        assert len(called) == 1

    def test_event_handler_receives_event_data(self):
        sm = SessionStateMachine("test-123")
        received = []

        def handler(event):
            received.append(event)

        sm.on("start_planning", handler)
        sm.transition("start_planning", {"test": "context"})

        assert len(received) == 1
        assert received[0].from_state == SessionState.GOAL_RECEIVED
        assert received[0].to_state == SessionState.PLANNING
        assert received[0].context == {"test": "context"}

    def test_event_handler_error_does_not_crash_transition(self):
        sm = SessionStateMachine("test-123")

        def bad_handler(event):
            raise ValueError("handler error")

        sm.on("start_planning", bad_handler)
        result = sm.transition("start_planning")

        assert result == SessionState.PLANNING
