import pytest
from src.planweaver.negotiator import Negotiator
from src.planweaver.models.plan import Plan, PlanStatus, ExecutionStep
from src.planweaver.models.session import (
    SessionState,
    NegotiatorIntent,
    PlanMutation,
    PlanMutationType,
)


class TestNegotiatorFallback:
    """Tests for Negotiator fallback behavior (when LLM fails)."""

    @pytest.fixture
    def negotiator(self):
        return Negotiator()

    @pytest.fixture
    def sample_plan(self):
        return Plan(
            session_id="test-123",
            user_intent="Build a web scraper",
            status=PlanStatus.AWAITING_APPROVAL,
        )

    def test_fallback_classifies_approval_yes(self, negotiator, sample_plan):
        output = negotiator._fallback_output("Yes, go ahead", sample_plan)
        assert output.intent == NegotiatorIntent.APPROVE

    def test_fallback_classifies_approval_execute(self, negotiator, sample_plan):
        output = negotiator._fallback_output("Execute the plan", sample_plan)
        assert output.intent == NegotiatorIntent.APPROVE

    def test_fallback_classifies_approval_do_it(self, negotiator, sample_plan):
        output = negotiator._fallback_output("Do it", sample_plan)
        assert output.intent == NegotiatorIntent.APPROVE

    def test_fallback_classifies_rejection(self, negotiator, sample_plan):
        output = negotiator._fallback_output("No, cancel", sample_plan)
        assert output.intent == NegotiatorIntent.REJECT

    def test_fallback_classifies_rejection_stop(self, negotiator, sample_plan):
        output = negotiator._fallback_output("Stop please", sample_plan)
        assert output.intent == NegotiatorIntent.REJECT

    def test_fallback_classifies_question(self, negotiator, sample_plan):
        output = negotiator._fallback_output("How long will this take?", sample_plan)
        assert output.intent == NegotiatorIntent.ASK_QUESTION

    def test_fallback_classifies_context_add(self, negotiator, sample_plan):
        output = negotiator._fallback_output("Add GitHub context", sample_plan)
        assert output.intent == NegotiatorIntent.PROVIDE_CONTEXT

    def test_fallback_classifies_revision_default(self, negotiator, sample_plan):
        output = negotiator._fallback_output("Make it simpler", sample_plan)
        assert output.intent == NegotiatorIntent.REVISE

    def test_fallback_low_confidence(self, negotiator, sample_plan):
        output = negotiator._fallback_output("Make it simpler", sample_plan)
        assert output.confidence == 0.3


class TestNegotiatorMutationApplication:
    """Tests for applying mutations to plans."""

    @pytest.fixture
    def negotiator(self):
        return Negotiator()

    @pytest.fixture
    def plan_with_steps(self):
        plan = Plan(
            session_id="test-123",
            user_intent="Build a web scraper",
            status=PlanStatus.AWAITING_APPROVAL,
        )
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="Set up project",
                prompt_template_id="default",
                assigned_model="gemini-2.5-flash",
            ),
            ExecutionStep(
                step_id=2,
                task="Write tests",
                prompt_template_id="default",
                assigned_model="gemini-2.5-flash",
                dependencies=[1],
            ),
        ]
        return plan

    def test_apply_lock_constraint(self, negotiator, plan_with_steps):
        mutations = [
            PlanMutation(
                mutation_type=PlanMutationType.LOCK_CONSTRAINT,
                key="timeout",
                value=30,
            )
        ]

        result_plan = negotiator.apply_mutations(mutations, plan_with_steps)
        assert result_plan.locked_constraints.get("timeout") == 30

    def test_apply_unlock_constraint(self, negotiator, plan_with_steps):
        plan_with_steps.lock_constraint("old_key", "old_value")

        mutations = [
            PlanMutation(
                mutation_type=PlanMutationType.UNLOCK_CONSTRAINT,
                key="old_key",
            )
        ]

        result_plan = negotiator.apply_mutations(mutations, plan_with_steps)
        assert "old_key" not in result_plan.locked_constraints

    def test_apply_add_step(self, negotiator, plan_with_steps):
        mutations = [
            PlanMutation(
                mutation_type=PlanMutationType.ADD_STEP,
                value="Deploy the scraper",
                step_id=2,
            )
        ]

        result_plan = negotiator.apply_mutations(mutations, plan_with_steps)
        assert len(result_plan.execution_graph) == 3
        new_step = result_plan.execution_graph[-1]
        assert new_step.task == "Deploy the scraper"
        assert new_step.step_id == 3

    def test_apply_edit_step(self, negotiator, plan_with_steps):
        mutations = [
            PlanMutation(
                mutation_type=PlanMutationType.EDIT_STEP,
                step_id=1,
                value="Set up project with Poetry",
            )
        ]

        result_plan = negotiator.apply_mutations(mutations, plan_with_steps)
        assert result_plan.execution_graph[0].task == "Set up project with Poetry"

    def test_apply_delete_step(self, negotiator, plan_with_steps):
        mutations = [
            PlanMutation(
                mutation_type=PlanMutationType.DELETE_STEP,
                step_id=2,
            )
        ]

        result_plan = negotiator.apply_mutations(mutations, plan_with_steps)
        assert len(result_plan.execution_graph) == 1
        assert result_plan.execution_graph[0].step_id == 1

    def test_delete_step_updates_dependencies(self, negotiator, plan_with_steps):
        mutations = [
            PlanMutation(
                mutation_type=PlanMutationType.DELETE_STEP,
                step_id=1,
            )
        ]

        result_plan = negotiator.apply_mutations(mutations, plan_with_steps)
        assert len(result_plan.execution_graph) == 1
        assert result_plan.execution_graph[0].dependencies == []


class TestNegotiatorContextBuilding:
    """Tests for context building in Negotiator."""

    @pytest.fixture
    def negotiator(self):
        return Negotiator()

    def test_build_context_includes_state(self, negotiator):
        plan = Plan(
            session_id="test-123",
            user_intent="Test intent",
            status=PlanStatus.BRAINSTORMING,
        )

        context = negotiator._build_context(plan, SessionState.PLANNING, None)

        assert "Session State: planning" in context
        assert "Plan Status: BRAINSTORMING" in context
        assert "Test intent" in context

    def test_build_context_with_constraints(self, negotiator):
        plan = Plan(
            session_id="test-123",
            user_intent="Test intent",
            status=PlanStatus.BRAINSTORMING,
        )
        plan.lock_constraint("framework", "FastAPI")

        context = negotiator._build_context(plan, SessionState.PLANNING, None)

        assert "Locked Constraints:" in context
        assert "framework" in context
        assert "FastAPI" in context

    def test_build_context_with_open_questions(self, negotiator):
        from src.planweaver.models.plan import OpenQuestion

        plan = Plan(
            session_id="test-123",
            user_intent="Test intent",
            status=PlanStatus.BRAINSTORMING,
        )
        plan.open_questions.append(OpenQuestion(question="What language?", answered=False))

        context = negotiator._build_context(plan, SessionState.CLARIFYING, None)

        assert "Open Questions:" in context
        assert "What language?" in context

    def test_build_context_with_execution_steps(self, negotiator):
        plan = Plan(
            session_id="test-123",
            user_intent="Test intent",
            status=PlanStatus.AWAITING_APPROVAL,
        )
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="First step task here",
                prompt_template_id="default",
                assigned_model="gemini-2.5-flash",
            ),
        ]

        context = negotiator._build_context(plan, SessionState.NEGOTIATING, None)

        assert "Execution Steps" in context
        assert "First step task here" in context

    def test_build_context_with_message_history(self, negotiator):
        plan = Plan(
            session_id="test-123",
            user_intent="Test intent",
            status=PlanStatus.AWAITING_APPROVAL,
        )

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        context = negotiator._build_context(plan, SessionState.NEGOTIATING, history)

        assert "Recent Conversation:" in context
        assert "Hello" in context
        assert "Hi there" in context
