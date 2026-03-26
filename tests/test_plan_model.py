import pytest
from datetime import datetime, timezone
from src.planweaver.models.plan import (
    Plan,
    ExecutionStep,
    StepStatus,
    PlanStatus,
    CandidatePlan,
    CandidatePlanStatus,
    PlanSourceType,
    OpenQuestion,
    StrawmanProposal,
    CandidatePlanRevision,
    PlanningOutcome,
)


class TestPlanBasicOperations:
    """Tests for Plan basic operations."""

    def test_add_open_question(self):
        plan = Plan(session_id="test", user_intent="Test")

        plan.add_open_question("What language?")

        assert len(plan.open_questions) == 1
        assert plan.open_questions[0].question == "What language?"
        assert plan.open_questions[0].answered is False

    def test_lock_constraint(self):
        plan = Plan(session_id="test", user_intent="Test")

        plan.lock_constraint("framework", "FastAPI")

        assert plan.locked_constraints["framework"] == "FastAPI"

    def test_add_step(self):
        plan = Plan(session_id="test", user_intent="Test")
        step = ExecutionStep(
            step_id=1,
            task="Test step",
            prompt_template_id="default",
            assigned_model="test",
        )

        plan.add_step(step)

        assert len(plan.execution_graph) == 1
        assert plan.execution_graph[0].task == "Test step"

    def test_updated_at_changes_on_modification(self):
        plan = Plan(session_id="test", user_intent="Test")
        original_time = plan.updated_at

        plan.lock_constraint("key", "value")

        assert plan.updated_at > original_time


class TestPlanGetPendingSteps:
    """Tests for Plan.get_pending_steps()."""

    def test_returns_only_pending_steps(self):
        plan = Plan(session_id="test", user_intent="Test")
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="Step 1",
                prompt_template_id="default",
                assigned_model="test",
                status=StepStatus.COMPLETED,
            ),
            ExecutionStep(
                step_id=2,
                task="Step 2",
                prompt_template_id="default",
                assigned_model="test",
                status=StepStatus.PENDING,
            ),
            ExecutionStep(
                step_id=3,
                task="Step 3",
                prompt_template_id="default",
                assigned_model="test",
                status=StepStatus.IN_PROGRESS,
            ),
        ]

        pending = plan.get_pending_steps()

        assert len(pending) == 1
        assert pending[0].step_id == 2

    def test_returns_empty_when_all_done(self):
        plan = Plan(session_id="test", user_intent="Test")
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="Step 1",
                prompt_template_id="default",
                assigned_model="test",
                status=StepStatus.COMPLETED,
            ),
        ]

        pending = plan.get_pending_steps()

        assert len(pending) == 0


class TestPlanCandidateOperations:
    """Tests for Plan candidate operations."""

    def test_get_candidate_by_id_found(self):
        plan = Plan(session_id="test", user_intent="Test")
        candidate = CandidatePlan(
            candidate_id="cand-123",
            title="Candidate 1",
            summary="Summary",
            source_type=PlanSourceType.LLM_GENERATED,
            source_model="test",
        )
        plan.candidate_plans = [candidate]

        result = plan.get_candidate_by_id("cand-123")

        assert result.candidate_id == "cand-123"

    def test_get_candidate_by_id_not_found(self):
        plan = Plan(session_id="test", user_intent="Test")

        with pytest.raises(ValueError, match="not found"):
            plan.get_candidate_by_id("nonexistent")

    def test_upsert_candidate_new(self):
        plan = Plan(session_id="test", user_intent="Test")
        candidate = CandidatePlan(
            candidate_id="cand-new",
            title="New Candidate",
            summary="Summary",
            source_type=PlanSourceType.LLM_GENERATED,
            source_model="test",
        )

        result = plan.upsert_candidate(candidate)

        assert len(plan.candidate_plans) == 1
        assert result.candidate_id == "cand-new"

    def test_upsert_candidate_existing_updates(self):
        plan = Plan(session_id="test", user_intent="Test")
        candidate = CandidatePlan(
            candidate_id="cand-123",
            title="Original",
            summary="Original summary",
            source_type=PlanSourceType.LLM_GENERATED,
            source_model="test",
        )
        plan.candidate_plans = [candidate]

        updated = CandidatePlan(
            candidate_id="cand-123",
            title="Updated",
            summary="Updated summary",
            source_type=PlanSourceType.LLM_GENERATED,
            source_model="test",
        )
        result = plan.upsert_candidate(updated)

        assert len(plan.candidate_plans) == 1
        assert plan.candidate_plans[0].title == "Updated"
        assert result.title == "Updated"

    def test_record_candidate_revision(self):
        plan = Plan(session_id="test", user_intent="Test")
        revision = CandidatePlanRevision(
            revision_id="rev-1",
            candidate_id="cand-123",
            revision_type="edit",
            title="Revised",
            summary="Summary",
            execution_graph=[],
        )

        plan.record_candidate_revision(revision)

        assert len(plan.candidate_revisions) == 1
        assert plan.candidate_revisions[0].revision_id == "rev-1"

    def test_record_outcome(self):
        plan = Plan(session_id="test", user_intent="Test")
        outcome = PlanningOutcome(
            outcome_id="out-1",
            session_id="test",
            event_type="completed",
            summary="Plan completed",
        )

        plan.record_outcome(outcome)

        assert len(plan.planning_outcomes) == 1
        assert plan.planning_outcomes[0].outcome_id == "out-1"


class TestPlanGetProposalById:
    """Tests for Plan.get_proposal_by_id()."""

    def test_get_proposal_by_id_found(self):
        plan = Plan(session_id="test", user_intent="Test")
        proposal = StrawmanProposal(
            id="prop-123",
            title="Proposal 1",
            description="Description",
        )
        plan.strawman_proposals = [proposal]

        result = plan.get_proposal_by_id("prop-123")

        assert result.id == "prop-123"

    def test_get_proposal_by_id_not_found(self):
        plan = Plan(session_id="test", user_intent="Test")

        with pytest.raises(ValueError, match="not found"):
            plan.get_proposal_by_id("nonexistent")


class TestCandidatePlanModel:
    """Tests for CandidatePlan model."""

    def test_candidate_plan_default_status(self):
        candidate = CandidatePlan(
            title="Test",
            summary="Summary",
            source_type=PlanSourceType.LLM_GENERATED,
            source_model="test",
        )

        assert candidate.status == CandidatePlanStatus.DRAFT

    def test_candidate_plan_default_planning_style(self):
        candidate = CandidatePlan(
            title="Test",
            summary="Summary",
            source_type=PlanSourceType.LLM_GENERATED,
            source_model="test",
        )

        assert candidate.planning_style == "baseline"

    def test_candidate_plan_timestamps(self):
        before = datetime.now(timezone.utc)
        candidate = CandidatePlan(
            title="Test",
            summary="Summary",
            source_type=PlanSourceType.LLM_GENERATED,
            source_model="test",
        )
        after = datetime.now(timezone.utc)

        assert before <= candidate.created_at <= after


class TestExecutionStepModel:
    """Tests for ExecutionStep model."""

    def test_execution_step_default_status(self):
        step = ExecutionStep(
            step_id=1,
            task="Test",
            prompt_template_id="default",
            assigned_model="test",
        )

        assert step.status == StepStatus.PENDING

    def test_execution_step_default_empty_dependencies(self):
        step = ExecutionStep(
            step_id=1,
            task="Test",
            prompt_template_id="default",
            assigned_model="test",
        )

        assert step.dependencies == []

    def test_execution_step_with_dependencies(self):
        step = ExecutionStep(
            step_id=1,
            task="Test",
            prompt_template_id="default",
            assigned_model="test",
            dependencies=[1, 2, 3],
        )

        assert step.dependencies == [1, 2, 3]


class TestOpenQuestionModel:
    """Tests for OpenQuestion model."""

    def test_open_question_default_unanswered(self):
        q = OpenQuestion(question="What?")

        assert q.answered is False
        assert q.answer is None

    def test_open_question_with_answer(self):
        q = OpenQuestion(question="What?", answer="This", answered=True)

        assert q.answered is True
        assert q.answer == "This"


class TestPlanStatusTransitions:
    """Tests for Plan status values."""

    def test_all_plan_statuses_valid(self):
        statuses = [
            PlanStatus.BRAINSTORMING,
            PlanStatus.AWAITING_APPROVAL,
            PlanStatus.APPROVED,
            PlanStatus.EXECUTING,
            PlanStatus.COMPLETED,
            PlanStatus.FAILED,
        ]

        assert len(statuses) == 6

    def test_plan_status_string_enum(self):
        assert PlanStatus.BRAINSTORMING.value == "BRAINSTORMING"
        assert PlanStatus.COMPLETED.value == "COMPLETED"


class TestStepStatusTransitions:
    """Tests for StepStatus values."""

    def test_all_step_statuses_valid(self):
        statuses = [
            StepStatus.PENDING,
            StepStatus.IN_PROGRESS,
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.SKIPPED,
        ]

        assert len(statuses) == 5
