import pytest
from unittest.mock import Mock
from decimal import Decimal

from planweaver.models.plan import (
    Plan,
    PlanStatus,
    StrawmanProposal,
    ExecutionStep,
    StepStatus,
    ProposalDetail,
    StepSummary,
)
from planweaver.services.comparison_service import ProposalComparisonService


class TestProposalComparisonService:
    @pytest.fixture
    def mock_planner(self):
        planner = Mock()
        planner.decompose_into_steps = Mock(return_value=[
            ExecutionStep(
                step_id=1,
                task="Install dependencies",
                prompt_template_id="default",
                assigned_model="gemini-2.5-flash",
                dependencies=[],
                status=StepStatus.PENDING,
            )
        ])
        return planner

    @pytest.fixture
    def mock_llm_gateway(self):
        return Mock()

    @pytest.fixture
    def comparison_service(self, mock_planner, mock_llm_gateway):
        return ProposalComparisonService(mock_planner, mock_llm_gateway)

    @pytest.fixture
    def sample_plan_with_proposals(self):
        plan = Plan(
            user_intent="Add authentication to API",
            status=PlanStatus.BRAINSTORMING
        )
        plan.strawman_proposals = [
            StrawmanProposal(
                id="prop-1",
                title="JWT Approach",
                description="Use JWT tokens",
                pros=["Scalable", "Standard"],
                cons=["Stateless"]
            ),
            StrawmanProposal(
                id="prop-2",
                title="Session Approach",
                description="Use server sessions",
                pros=["Simple", "Secure"],
                cons=["Server state"]
            )
        ]
        return plan

    def test_compare_proposals_requires_at_least_two(
        self, comparison_service, sample_plan_with_proposals
    ):
        """Should raise error if fewer than 2 proposals"""
        with pytest.raises(ValueError, match="at least 2 proposals"):
            comparison_service.compare_proposals(sample_plan_with_proposals, ["prop-1"])

    def test_compare_proposals_creates_comparison(
        self, comparison_service, sample_plan_with_proposals
    ):
        """Should create comparison with valid structure"""
        result = comparison_service.compare_proposals(
            sample_plan_with_proposals,
            ["prop-1", "prop-2"]
        )

        assert result.session_id == sample_plan_with_proposals.session_id
        assert len(result.proposals) == 2
        assert "common_steps" in result.model_dump()
        assert "unique_steps_by_proposal" in result.model_dump()
        assert "time_comparison" in result.model_dump()
        assert "cost_comparison" in result.model_dump()

    def test_estimate_time_weights_complexity(self, comparison_service):
        """Complex steps should take longer"""
        simple_steps = [
            ExecutionStep(
                step_id=1,
                task="Install package",
                prompt_template_id="default",
                assigned_model="gemini-2.5-flash",
                dependencies=[],
                status=StepStatus.PENDING,
            )
        ]
        complex_steps = [
            ExecutionStep(
                step_id=1,
                task="Migrate database architecture",
                prompt_template_id="default",
                assigned_model="gemini-2.5-flash",
                dependencies=[],
                status=StepStatus.PENDING,
            )
        ]

        simple_time = comparison_service._estimate_time(simple_steps)
        complex_time = comparison_service._estimate_time(complex_steps)

        assert complex_time > simple_time

    def test_estimate_cost_returns_valid_decimal(self, comparison_service):
        """Should return valid decimal cost"""
        steps = [
            ExecutionStep(
                step_id=1,
                task="Test step",
                prompt_template_id="default",
                assigned_model="gemini-2.5-flash",
                dependencies=[],
                status=StepStatus.PENDING,
            )
        ]

        cost = comparison_service._estimate_cost(steps)

        assert isinstance(cost, Decimal)
        assert cost >= 0

    def test_infer_complexity_from_keywords(self, comparison_service):
        """Complexity inference based on keywords"""
        high_step = ExecutionStep(
            step_id=1,
            task="Migrate database architecture",
            prompt_template_id="default",
            assigned_model="gemini-2.5-flash",
            dependencies=[],
            status=StepStatus.PENDING,
        )
        low_step = ExecutionStep(
            step_id=2,
            task="Install package",
            prompt_template_id="default",
            assigned_model="gemini-2.5-flash",
            dependencies=[],
            status=StepStatus.PENDING,
        )
        medium_step = ExecutionStep(
            step_id=3,
            task="Refactor the component",
            prompt_template_id="default",
            assigned_model="gemini-2.5-flash",
            dependencies=[],
            status=StepStatus.PENDING,
        )

        assert comparison_service._infer_step_complexity(high_step) == "High"
        assert comparison_service._infer_step_complexity(low_step) == "Low"
        # "Refactor" makes it high complexity
        assert comparison_service._infer_step_complexity(medium_step) == "High"

    def test_extract_risks_identifies_keywords(self, comparison_service):
        """Should identify risk keywords in steps"""
        steps = [
            ExecutionStep(
                step_id=1,
                task="Deploy to production server",
                prompt_template_id="default",
                assigned_model="gemini-2.5-flash",
                dependencies=[],
                status=StepStatus.PENDING,
            ),
            ExecutionStep(
                step_id=2,
                task="Migrate user database",
                prompt_template_id="default",
                assigned_model="gemini-2.5-flash",
                dependencies=[],
                status=StepStatus.PENDING,
            ),
            ExecutionStep(
                step_id=3,
                task="Call external API",
                prompt_template_id="default",
                assigned_model="gemini-2.5-flash",
                dependencies=[],
                status=StepStatus.PENDING,
            )
        ]

        risks = comparison_service._extract_risks(steps)

        assert len(risks) > 0
        assert any("production" in r.lower() for r in risks)
        assert any("migration" in r.lower() for r in risks)

    def test_find_common_steps_no_proposals(self, comparison_service):
        """Should return empty list if no proposals"""
        result = comparison_service._find_common_steps([])
        assert result == []

    def test_estimate_time_no_steps(self, comparison_service):
        """Should return 0 for empty steps"""
        result = comparison_service._estimate_time([])
        assert result == 0

    def test_has_similar_step_exact_match(self, comparison_service):
        """Should match steps with identical tasks"""
        step1 = ExecutionStep(
            step_id=1,
            task="Create project structure",
            prompt_template_id="default",
            assigned_model="gemini-2.5-flash",
            dependencies=[],
            status=StepStatus.PENDING,
        )
        step2 = ExecutionStep(
            step_id=2,
            task="Create project structure",
            prompt_template_id="default",
            assigned_model="gemini-2.5-flash",
            dependencies=[],
            status=StepStatus.PENDING,
        )

        assert comparison_service._has_similar_step(step1, [step2])

    def test_has_similar_step_fuzzy_match(self, comparison_service):
        """Should match steps with similar tasks using word overlap"""
        step1 = ExecutionStep(
            step_id=1,
            task="Create database schema",
            prompt_template_id="default",
            assigned_model="gemini-2.5-flash",
            dependencies=[],
            status=StepStatus.PENDING,
        )
        step2 = ExecutionStep(
            step_id=2,
            task="Update database schema",
            prompt_template_id="default",
            assigned_model="gemini-2.5-flash",
            dependencies=[],
            status=StepStatus.PENDING,
        )
        # These share "database" and "schema" - should match

        assert comparison_service._has_similar_step(step1, [step2])

    def test_calculate_complexity_score(self, comparison_service):
        """Should calculate overall proposal complexity"""
        high_proposal = ProposalDetail(
            proposal_id="1",
            full_execution_graph=[
                ExecutionStep(
                    step_id=i,
                    task=f"Migration task {i}",
                    prompt_template_id="default",
                    assigned_model="gemini-2.5-flash",
                    dependencies=[],
                    status=StepStatus.PENDING,
                )
                for i in range(5)
            ],
            accurate_time_estimate=10,
            accurate_cost_estimate=Decimal("0.01"),
            all_risk_factors=[]
        )

        low_proposal = ProposalDetail(
            proposal_id="2",
            full_execution_graph=[
                ExecutionStep(
                    step_id=i,
                    task=f"Install package {i}",
                    prompt_template_id="default",
                    assigned_model="gemini-2.5-flash",
                    dependencies=[],
                    status=StepStatus.PENDING,
                )
                for i in range(5)
            ],
            accurate_time_estimate=10,
            accurate_cost_estimate=Decimal("0.01"),
            all_risk_factors=[]
        )

        high_score = comparison_service._calculate_complexity_score(high_proposal)
        low_score = comparison_service._calculate_complexity_score(low_proposal)

        assert high_score == "High"
        assert low_score == "Low"

    def test_clear_cache(self, comparison_service):
        """Should clear the graph cache"""
        # Add something to cache
        comparison_service._graph_cache[("test", "prop-1")] = []

        comparison_service.clear_cache()

        assert len(comparison_service._graph_cache) == 0
