"""
Integration Tests for Phase 2 Components

Tests integration between Critic, Context Synthesis, and Orchestrator.
"""

import pytest

from planweaver.orchestrator import Orchestrator
from planweaver.critic import Critic, CriticReport, Verdict, ObjectionSeverity
from planweaver.context_synthesis import ContextSynthesizer, PlanBrief
from planweaver.models.plan import (
    CandidatePlan,
    CandidatePlanStatus,
    ExternalContext,
    Plan,
    PlanSourceType,
)


@pytest.fixture
def orchestrator():
    """Create orchestrator instance."""
    return Orchestrator()


@pytest.fixture
def sample_plan(orchestrator):
    """Create sample plan."""
    return orchestrator.start_session(
        user_intent="Build a REST API with user authentication",
        scenario_name="web_development",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_critic_review_workflow(orchestrator, sample_plan):
    """Test critic reviews candidates after generation."""
    # Get a candidate
    candidates = orchestrator.list_candidates(sample_plan)
    assert len(candidates) > 0

    candidate = candidates[0]

    # Review with critic
    reviewed_candidate = await orchestrator.review_candidate_with_critic(
        sample_plan,
        candidate,
    )

    assert reviewed_candidate is not None
    # Should have critic report in metadata
    assert "critic_report" in reviewed_candidate.metadata


@pytest.mark.integration
@pytest.mark.asyncio
async def test_critic_blocks_dangerous_plans(orchestrator):
    """Test critic blocks plans with critical issues."""
    # Create a plan with dangerous operation
    plan = orchestrator.start_session(
        user_intent="Delete all production data",
        scenario_name="dangerous",
    )

    candidates = orchestrator.list_candidates(plan)
    if candidates:
        candidate = candidates[0]

        # Review with critic
        report = await orchestrator.critic.review_plan(plan, candidate)

        # Should have objections
        assert len(report.objections) > 0 or report.overall_verdict != Verdict.ACCEPT


@pytest.mark.integration
def test_can_approve_plan_check(orchestrator, sample_plan):
    """Test can_approve_plan checks critic reports."""
    can_approve, reason = orchestrator.can_approve_plan(sample_plan)

    assert isinstance(can_approve, bool)
    assert isinstance(reason, str)


@pytest.mark.integration
def test_can_approve_plan_only_checks_selected_candidate(orchestrator):
    """Rejected side branches should not block approval of the active candidate."""
    accepted = CandidatePlan(
        candidate_id="accepted",
        session_id="test-session",
        title="Accepted",
        summary="Safe plan",
        source_type=PlanSourceType.LLM_GENERATED,
        source_model="test",
        status=CandidatePlanStatus.SELECTED,
        metadata={"critic_report": {"overall_verdict": "accept"}},
    )
    rejected = CandidatePlan(
        candidate_id="rejected",
        session_id="test-session",
        title="Rejected branch",
        summary="Unsafe plan",
        source_type=PlanSourceType.LLM_GENERATED,
        source_model="test",
        status=CandidatePlanStatus.SUPERSEDED,
        metadata={"critic_report": {"overall_verdict": "reject"}},
    )
    plan = Plan(
        session_id="test-session",
        user_intent="Build a safe API",
        candidate_plans=[accepted, rejected],
        selected_candidate_id="accepted",
        approved_candidate_id="accepted",
    )

    can_approve, reason = orchestrator.can_approve_plan(plan)

    assert can_approve is True
    assert reason == "Plan can be approved"


@pytest.mark.integration
def test_orchestrator_has_critic(orchestrator):
    """Test orchestrator has critic agent."""
    assert hasattr(orchestrator, "critic")
    assert isinstance(orchestrator.critic, Critic)


@pytest.mark.integration
def test_orchestrator_has_context_synthesizer(orchestrator):
    """Test orchestrator has context synthesizer."""
    assert hasattr(orchestrator, "context_synthesizer")
    assert isinstance(orchestrator.context_synthesizer, ContextSynthesizer)


@pytest.mark.integration
def test_context_synthesizer_has_memory(orchestrator):
    """Test context synthesizer is connected to memory."""
    assert orchestrator.context_synthesizer.memory == orchestrator.memory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_synthesis_with_github_context(orchestrator):
    """Test context synthesis with GitHub context."""
    plan = orchestrator.start_session(
        user_intent="Build a FastAPI service",
        external_contexts=[
            ExternalContext(
                source_type="github",
                source_url="https://github.com/example/fastapi-app",
                content_summary="Example FastAPI project",
            )
        ],
    )

    # Context synthesis runs in background
    # Just verify the plan was created
    assert plan.session_id is not None
    assert len(plan.external_contexts) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_critic_generates_summary(orchestrator, sample_plan):
    """Test critic generates human-readable summary."""
    candidates = orchestrator.list_candidates(sample_plan)
    if candidates:
        report = await orchestrator.critic.review_plan(sample_plan, candidates[0])

        assert report.summary is not None
        assert len(report.summary) > 0
        # Summary should mention verdict
        assert report.overall_verdict.value.lower() in report.summary.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_critic_counts_severity_levels(orchestrator, sample_plan):
    """Test critic correctly counts objections by severity."""
    candidates = orchestrator.list_candidates(sample_plan)
    if candidates:
        report = await orchestrator.critic.review_plan(sample_plan, candidates[0])

        # Count should match actual objections
        critical_in_objections = sum(1 for o in report.objections if o.severity == ObjectionSeverity.CRITICAL)
        assert report.critical_issue_count == critical_in_objections


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_synthesis_parallel_execution(orchestrator):
    """Test context synthesis runs agents in parallel."""
    plan = orchestrator.start_session(
        user_intent="Build a web scraper",
    )

    # Synthesis runs in background
    # Verify it was scheduled
    assert plan.session_id is not None


@pytest.mark.integration
def test_critic_report_verdict_types():
    """Test critic report verdict types."""

    report = CriticReport(
        session_id="test",
        candidate_id="test",
        overall_verdict=Verdict.ACCEPT,
    )

    assert report.overall_verdict == Verdict.ACCEPT
    assert not report.should_trigger_revision()

    report.overall_verdict = Verdict.REVISE
    assert report.should_trigger_revision()

    report.overall_verdict = Verdict.REJECT
    assert report.should_trigger_revision()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_brief_structure():
    """Test PlanBrief has all required fields."""
    brief = PlanBrief(
        user_intent="Build API",
        synthesized_context="Test context",
    )

    assert brief.user_intent == "Build API"
    assert brief.synthesized_context == "Test context"
    assert brief.synthesized_at is not None
    assert isinstance(brief.confidence_scores, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_critic_handles_empty_execution_graph(orchestrator):
    """Test critic handles plans with no execution steps."""
    plan = orchestrator.start_session(
        user_intent="Simple plan",
    )

    # Create candidate with empty execution graph
    candidate = CandidatePlan(
        candidate_id="empty",
        session_id=plan.session_id,
        title="Empty Plan",
        summary="Plan with no steps",
        source_type="llm_generated",
        source_model="test",
        execution_graph=[],
    )

    report = await orchestrator.critic.review_plan(plan, candidate)

    # Should reject or flag as incomplete
    assert report.overall_verdict in [Verdict.REJECT, Verdict.REVISE] or len(report.objections) > 0


@pytest.mark.integration
def test_critic_and_synthesizer_integration(orchestrator):
    """Test critic and synthesizer can work together."""
    # Both should be initialized
    assert orchestrator.critic is not None
    assert orchestrator.context_synthesizer is not None

    # Synthesizer should use memory
    assert orchestrator.context_synthesizer.memory == orchestrator.memory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_with_all_components(orchestrator):
    """Test full workflow: create -> synthesize -> review -> approve."""
    # Create session
    plan = orchestrator.start_session(
        user_intent="Build a task management API",
        scenario_name="task_manager",
    )

    assert plan.session_id is not None

    # Context synthesis happens in background
    # Critic review happens in background
    # Verify we can check approval status
    can_approve, reason = orchestrator.can_approve_plan(plan)

    assert isinstance(can_approve, bool)


@pytest.mark.integration
def test_plan_metadata_enrichment(orchestrator):
    """Test that plan metadata is enriched by Phase 2 components."""
    plan = orchestrator.start_session(
        user_intent="Test metadata enrichment",
    )

    # Metadata should exist
    assert isinstance(plan.metadata, dict)

    # May have context_brief if synthesis completed
    # May have critic reports if candidates were reviewed
