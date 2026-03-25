"""
Tests for Critic Agent for Plan Review
"""

import pytest
from unittest.mock import Mock, AsyncMock

from planweaver.critic import (
    Critic,
    CriticObjection,
    CriticReport,
    ObjectionSeverity,
    ObjectionCategory,
    Verdict,
)
from planweaver.models.plan import Plan, CandidatePlan, ExecutionStep, StepStatus
from planweaver.services.llm_gateway import LLMGateway


@pytest.fixture
def mock_llm_gateway():
    """Mock LLM gateway."""
    gateway = Mock(spec=LLMGateway)
    return gateway


@pytest.fixture
def critic(mock_llm_gateway):
    """Create critic instance."""
    return Critic(mock_llm_gateway)


@pytest.fixture
def sample_plan():
    """Create sample plan."""
    return Plan(
        session_id="test_session_123",
        user_intent="Build a REST API with user authentication",
        scenario_name="web_development",
        status="BRAINSTORMING",
    )


@pytest.fixture
def sample_candidate():
    """Create sample candidate plan."""
    steps = [
        ExecutionStep(
            step_id=1,
            task="Set up FastAPI project structure",
            prompt_template_id="default",
            assigned_model="gemini-3-flash",
            status=StepStatus.PENDING,
        ),
        ExecutionStep(
            step_id=2,
            task="Implement user authentication endpoints",
            prompt_template_id="default",
            assigned_model="gemini-3-flash",
            status=StepStatus.PENDING,
            dependencies=[1],
        ),
        ExecutionStep(
            step_id=3,
            task="Add unit tests for authentication",
            prompt_template_id="default",
            assigned_model="gemini-3-flash",
            status=StepStatus.PENDING,
            dependencies=[2],
        ),
    ]

    return CandidatePlan(
        candidate_id="candidate_123",
        session_id="test_session_123",
        title="REST API with Authentication",
        summary="Build FastAPI REST API with JWT authentication",
        source_type="llm_generated",
        source_model="gemini-2.5-flash",
        planning_style="baseline",
        execution_graph=steps,
    )


def test_critic_initialization(critic):
    """Test critic initialization."""
    assert critic.llm is not None


@pytest.mark.asyncio
async def test_review_plan_success(critic, sample_plan, sample_candidate):
    """Test successful plan review."""
    report = await critic.review_plan(sample_plan, sample_candidate)

    assert isinstance(report, CriticReport)
    assert report.session_id == sample_plan.session_id
    assert report.candidate_id == sample_candidate.candidate_id
    assert report.overall_verdict in [Verdict.ACCEPT, Verdict.REVISE, Verdict.REJECT]


@pytest.mark.asyncio
async def test_review_plan_with_critical_issues(critic, sample_plan):
    """Test review with critical issues."""
    # Create candidate with no execution steps
    candidate = CandidatePlan(
        candidate_id="candidate_empty",
        session_id=sample_plan.session_id,
        title="Empty Plan",
        summary="Plan with no steps",
        source_type="llm_generated",
        source_model="gemini-2.5-flash",
        execution_graph=[],
    )

    report = await critic.review_plan(sample_plan, candidate)

    assert report.overall_verdict == Verdict.REJECT
    assert report.critical_issue_count > 0


@pytest.mark.asyncio
async def test_review_plan_identifies_vague_tasks(critic, sample_plan, sample_candidate):
    """Test that critic identifies vague tasks."""
    # Add vague task
    vague_step = ExecutionStep(
        step_id=4,
        task="Handle the authentication",
        prompt_template_id="default",
        assigned_model="gemini-3-flash",
        status=StepStatus.PENDING,
    )
    sample_candidate.execution_graph.append(vague_step)

    report = await critic.review_plan(sample_plan, sample_candidate)

    # Should have at least one objection
    assert len(report.objections) > 0


@pytest.mark.asyncio
async def test_review_plan_checks_dependencies(critic, sample_plan, sample_candidate):
    """Test that critic validates dependencies."""
    # Add step with invalid dependency
    invalid_step = ExecutionStep(
        step_id=5,
        task="Test invalid dependency",
        prompt_template_id="default",
        assigned_model="gemini-3-flash",
        status=StepStatus.PENDING,
        dependencies=[99],  # Non-existent step
    )
    sample_candidate.execution_graph.append(invalid_step)

    report = await critic.review_plan(sample_plan, sample_candidate)

    # Should have objection for invalid dependency
    dependency_objections = [
        o
        for o in report.objections
        if o.category == ObjectionCategory.LOGIC and "depends on non-existent" in o.description
    ]
    assert len(dependency_objections) > 0


@pytest.mark.asyncio
async def test_review_plan_checks_completeness(critic, sample_plan, sample_candidate):
    """Test that critic checks plan completeness."""
    # Remove testing steps
    sample_candidate.execution_graph = [
        step for step in sample_candidate.execution_graph if "test" not in step.task.lower()
    ]

    report = await critic.review_plan(sample_plan, sample_candidate)

    # Should have objection about missing testing
    completeness_objections = [
        o
        for o in report.objections
        if o.category == ObjectionCategory.COMPLETENESS and "testing" in o.description.lower()
    ]
    assert len(completeness_objections) > 0


@pytest.mark.asyncio
async def test_review_plan_checks_safety(critic, sample_plan):
    """Test that critic identifies safety concerns."""
    # Add dangerous step
    dangerous_step = ExecutionStep(
        step_id=1,
        task="Delete all user data",
        prompt_template_id="default",
        assigned_model="gemini-3-flash",
        status=StepStatus.PENDING,
    )

    candidate = CandidatePlan(
        candidate_id="candidate_dangerous",
        session_id=sample_plan.session_id,
        title="Dangerous Plan",
        summary="Plan with dangerous operation",
        source_type="llm_generated",
        source_model="gemini-2.5-flash",
        execution_graph=[dangerous_step],
    )

    report = await critic.review_plan(sample_plan, candidate)

    # Should have safety objection
    safety_objections = [o for o in report.objections if o.category == ObjectionCategory.SAFETY]
    assert len(safety_objections) > 0


def test_critic_report_has_critical_issues(sample_plan, sample_candidate):
    """Test CriticReport.has_critical_issues method."""
    report = CriticReport(
        session_id=sample_plan.session_id,
        candidate_id=sample_candidate.candidate_id,
        objections=[],
        overall_verdict=Verdict.ACCEPT,
        critical_issue_count=0,
    )

    assert not report.has_critical_issues()

    report.critical_issue_count = 1
    assert report.has_critical_issues()


def test_critic_report_should_trigger_revision(sample_plan, sample_candidate):
    """Test CriticReport.should_trigger_revision method."""
    report_accept = CriticReport(
        session_id=sample_plan.session_id,
        candidate_id=sample_candidate.candidate_id,
        objections=[],
        overall_verdict=Verdict.ACCEPT,
        critical_issue_count=0,
    )

    assert not report_accept.should_trigger_revision()

    report_revise = CriticReport(
        session_id=sample_plan.session_id,
        candidate_id=sample_candidate.candidate_id,
        objections=[],
        overall_verdict=Verdict.REVISE,
        critical_issue_count=0,
    )

    assert report_revise.should_trigger_revision()

    report_reject = CriticReport(
        session_id=sample_plan.session_id,
        candidate_id=sample_candidate.candidate_id,
        objections=[],
        overall_verdict=Verdict.REJECT,
        critical_issue_count=1,
    )

    assert report_reject.should_trigger_revision()


def test_critic_objection_severity_enum():
    """Test ObjectionSeverity enum values."""
    assert ObjectionSeverity.CRITICAL == "critical"
    assert ObjectionSeverity.HIGH == "high"
    assert ObjectionSeverity.MEDIUM == "medium"
    assert ObjectionSeverity.LOW == "low"


def test_critic_objection_category_enum():
    """Test ObjectionCategory enum values."""
    assert ObjectionCategory.LOGIC == "logic"
    assert ObjectionCategory.FEASIBILITY == "feasibility"
    assert ObjectionCategory.COMPLETENESS == "completeness"
    assert ObjectionCategory.SAFETY == "safety"
    assert ObjectionCategory.COST == "cost"


def test_critic_verdict_enum():
    """Test Verdict enum values."""
    assert Verdict.ACCEPT == "accept"
    assert Verdict.REVISE == "revise"
    assert Verdict.REJECT == "reject"


def test_is_vague_task(critic):
    """Test vague task detection."""
    assert critic._is_vague_task("Handle the authentication")
    assert critic._is_vague_task("Process the data")
    assert not critic._is_vague_task("Create a JWT authentication endpoint with user login")


def test_is_overly_complex(critic):
    """Test overly complex task detection."""
    complex_task = (
        "Create and update and delete multiple items while also managing dependencies and implementing error handling"
    )
    assert critic._is_overly_complex(complex_task)

    simple_task = "Create user authentication endpoint"
    assert not critic._is_overly_complex(simple_task)


def test_determine_verdict(critic):
    """Test verdict determination logic."""
    # No objections -> accept
    verdict = critic._determine_verdict([], 0, 0)
    assert verdict == Verdict.ACCEPT

    # Critical issues -> reject
    verdict = critic._determine_verdict([], 1, 0)
    assert verdict == Verdict.REJECT

    # Many high issues -> revise
    verdict = critic._determine_verdict([], 0, 3)
    assert verdict == Verdict.REVISE


def test_calculate_confidence(critic):
    """Test confidence calculation."""
    objections = [
        CriticObjection(
            severity=ObjectionSeverity.HIGH,
            category=ObjectionCategory.LOGIC,
            description="Test objection 1",
            confidence=0.8,
        ),
        CriticObjection(
            severity=ObjectionSeverity.MEDIUM,
            category=ObjectionCategory.COMPLETENESS,
            description="Test objection 2",
            confidence=0.6,
        ),
    ]

    confidence = critic._calculate_confidence(objections)
    assert confidence == 0.7  # Average of 0.8 and 0.6


def test_should_trigger_revision_method(critic):
    """Test Critic.should_trigger_revision method."""
    report_accept = CriticReport(
        session_id="test",
        candidate_id="test",
        overall_verdict=Verdict.ACCEPT,
    )

    assert not critic.should_trigger_revision(report_accept)

    report_revise = CriticReport(
        session_id="test",
        candidate_id="test",
        overall_verdict=Verdict.REVISE,
    )

    assert critic.should_trigger_revision(report_revise)


@pytest.mark.asyncio
async def test_review_plan_error_handling(critic, sample_plan, sample_candidate):
    """Test that critic handles errors gracefully."""
    # Mock to raise exception
    original_analyze = critic._analyze_completeness
    critic._analyze_completeness = AsyncMock(side_effect=Exception("Test error"))

    report = await critic.review_plan(sample_plan, sample_candidate)

    # Should return a default accept report on error
    assert report.overall_verdict == Verdict.ACCEPT
    assert "failed" in report.summary.lower()

    # Restore original method
    critic._analyze_completeness = original_analyze
