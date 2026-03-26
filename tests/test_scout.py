import pytest
from unittest.mock import AsyncMock, patch
from src.planweaver.models.plan import ExecutionStep, Plan
from src.planweaver.scout import PreconditionScout, ScoutReport


class TestScoutPreconditionExtraction:
    """Tests for precondition extraction from task text."""

    @pytest.fixture
    def scout(self):
        return PreconditionScout()

    def test_extracts_service_precondition_from_port_format(self, scout):
        preconditions = scout._identify_preconditions(
            [
                ExecutionStep(
                    step_id=1,
                    task="Confirm port 5432 on localhost is open before running migrations.",
                    prompt_template_id="default",
                    assigned_model="test-model",
                )
            ]
        )

        assert len(preconditions) == 1
        assert preconditions[0].precondition_type == "service_running"
        assert preconditions[0].check_expression == "localhost:5432"

    def test_no_preconditions_in_regular_task(self, scout):
        preconditions = scout._identify_preconditions(
            [
                ExecutionStep(
                    step_id=1,
                    task="Write unit tests for the calculator module.",
                    prompt_template_id="default",
                    assigned_model="test",
                )
            ]
        )

        assert len(preconditions) == 0

    def test_service_running_with_port_keyword(self, scout):
        preconditions = scout._identify_preconditions(
            [
                ExecutionStep(
                    step_id=1,
                    task="Ensure port 8080 on localhost is open before starting server.",
                    prompt_template_id="default",
                    assigned_model="test",
                )
            ]
        )

        assert len(preconditions) == 1
        assert preconditions[0].precondition_type == "service_running"
        assert "localhost:8080" in preconditions[0].check_expression

    def test_multiple_steps_with_preconditions(self, scout):
        preconditions = scout._identify_preconditions(
            [
                ExecutionStep(
                    step_id=1,
                    task="Confirm port 5432 on localhost is open before running migrations.",
                    prompt_template_id="default",
                    assigned_model="test-model",
                ),
                ExecutionStep(
                    step_id=2,
                    task="Ensure port 9090 on remotehost is open before starting.",
                    prompt_template_id="default",
                    assigned_model="test-model",
                ),
            ]
        )

        assert len(preconditions) == 2
        types = {p.precondition_type for p in preconditions}
        assert "service_running" in types

    def test_step_ids_preserved_in_preconditions(self, scout):
        preconditions = scout._identify_preconditions(
            [
                ExecutionStep(
                    step_id=5,
                    task="Ensure port 9090 on localhost is open.",
                    prompt_template_id="default",
                    assigned_model="test",
                ),
            ]
        )

        assert len(preconditions) == 1
        assert preconditions[0].step_id == 5


class TestScoutPlanAnnotation:
    """Tests for plan annotation with precondition results."""

    @pytest.fixture
    def scout(self):
        return PreconditionScout()

    @pytest.fixture
    def plan_with_steps(self):
        return Plan(
            session_id="test-123",
            user_intent="Deploy application",
            execution_graph=[
                ExecutionStep(
                    step_id=1,
                    task="Check file exists",
                    prompt_template_id="default",
                    assigned_model="test",
                ),
                ExecutionStep(
                    step_id=2,
                    task="Check API reachable",
                    prompt_template_id="default",
                    assigned_model="test",
                    dependencies=[1],
                ),
            ],
        )

    def test_annotate_plan_empty_report(self, scout, plan_with_steps):
        report = ScoutReport(preconditions=[], failed=[], unverifiable=[])

        result = scout.annotate_plan(plan_with_steps, report)

        assert result.execution_graph[0].preconditions == []
        assert result.execution_graph[1].preconditions == []

    def test_annotate_plan_with_results(self, scout, plan_with_steps):
        from src.planweaver.scout import PreconditionResult

        report = ScoutReport(
            preconditions=[
                PreconditionResult(
                    step_id=1,
                    precondition_type="file_exists",
                    check_expression="/path/file.txt",
                    probe_result=True,
                    probe_error=None,
                )
            ],
            failed=[],
            unverifiable=[],
        )

        result = scout.annotate_plan(plan_with_steps, report)

        assert len(result.execution_graph[0].preconditions) == 1
        assert result.execution_graph[0].preconditions[0].precondition_type == "file_exists"
        assert result.execution_graph[0].preconditions[0].probe_result is True

    def test_annotate_plan_multiple_preconditions_same_step(self, scout):
        from src.planweaver.scout import PreconditionResult

        plan = Plan(
            session_id="test-123",
            user_intent="Test",
            execution_graph=[
                ExecutionStep(
                    step_id=1,
                    task="Check multiple things",
                    prompt_template_id="default",
                    assigned_model="test",
                ),
            ],
        )
        report = ScoutReport(
            preconditions=[
                PreconditionResult(
                    step_id=1,
                    precondition_type="file_exists",
                    check_expression="file1.txt",
                    probe_result=True,
                    probe_error=None,
                ),
                PreconditionResult(
                    step_id=1,
                    precondition_type="import_available",
                    check_expression="os",
                    probe_result=True,
                    probe_error=None,
                ),
            ],
            failed=[],
            unverifiable=[],
        )

        result = scout.annotate_plan(plan, report)

        assert len(result.execution_graph[0].preconditions) == 2


class TestScoutReport:
    """Tests for ScoutReport methods."""

    def test_has_failed_preconditions_true(self):
        from src.planweaver.scout import PreconditionResult, ScoutReport

        report = ScoutReport(
            preconditions=[],
            failed=[
                PreconditionResult(
                    step_id=1,
                    precondition_type="file_exists",
                    check_expression="/missing.txt",
                    probe_result=False,
                    probe_error=None,
                )
            ],
            unverifiable=[],
        )

        assert report.has_failed_preconditions() is True

    def test_has_failed_preconditions_false(self):
        from src.planweaver.scout import ScoutReport

        report = ScoutReport(
            preconditions=[],
            failed=[],
            unverifiable=[],
        )

        assert report.has_failed_preconditions() is False

    def test_format_failed_message_empty(self):
        from src.planweaver.scout import ScoutReport

        report = ScoutReport(preconditions=[], failed=[], unverifiable=[])

        assert report.format_failed_message() == ""

    def test_format_failed_message_with_failures(self):
        from src.planweaver.scout import PreconditionResult, ScoutReport

        report = ScoutReport(
            preconditions=[],
            failed=[
                PreconditionResult(
                    step_id=1,
                    precondition_type="file_exists",
                    check_expression="/missing.txt",
                    probe_result=False,
                    probe_error=None,
                ),
                PreconditionResult(
                    step_id=2,
                    precondition_type="import_available",
                    check_expression="missing_lib",
                    probe_result=False,
                    probe_error="Unknown module",
                ),
            ],
            unverifiable=[],
        )

        message = report.format_failed_message()

        assert "Precondition validation failed" in message
        assert "Step 1" in message
        assert "Step 2" in message
        assert "Unknown module" in message


class TestScoutScoutPlan:
    """Tests for scout_plan method with mocked probes."""

    @pytest.fixture
    def scout(self):
        return PreconditionScout()

    @pytest.mark.asyncio
    async def test_scout_plan_no_preconditions(self, scout):
        plan = Plan(
            session_id="test-123",
            user_intent="Simple task",
            execution_graph=[
                ExecutionStep(
                    step_id=1,
                    task="Just do something",
                    prompt_template_id="default",
                    assigned_model="test",
                ),
            ],
        )

        report = await scout.scout_plan(plan)

        assert len(report.preconditions) == 0
        assert len(report.failed) == 0

    @pytest.mark.asyncio
    async def test_scout_plan_with_successful_probe(self, scout):
        from src.planweaver.probes.base import ProbeResult

        plan = Plan(
            session_id="test-123",
            user_intent="Test",
            execution_graph=[
                ExecutionStep(
                    step_id=1,
                    task="Confirm port 5432 on localhost is open before running migrations.",
                    prompt_template_id="default",
                    assigned_model="test",
                ),
            ],
        )

        with patch("src.planweaver.scout.run_probe", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ProbeResult(success=True, result=True)

            report = await scout.scout_plan(plan)

            assert len(report.preconditions) == 1
            assert report.preconditions[0].probe_result is True
            assert len(report.failed) == 0

    @pytest.mark.asyncio
    async def test_scout_plan_with_failed_probe(self, scout):
        from src.planweaver.probes.base import ProbeResult

        plan = Plan(
            session_id="test-123",
            user_intent="Test",
            execution_graph=[
                ExecutionStep(
                    step_id=1,
                    task="Confirm port 9999 on localhost is open before starting.",
                    prompt_template_id="default",
                    assigned_model="test",
                ),
            ],
        )

        with patch("src.planweaver.scout.run_probe", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ProbeResult(success=True, result=False)

            report = await scout.scout_plan(plan)

            assert len(report.preconditions) == 1
            assert report.preconditions[0].probe_result is False
            assert len(report.failed) == 1

    @pytest.mark.asyncio
    async def test_scout_plan_handles_probe_exception(self, scout):
        plan = Plan(
            session_id="test-123",
            user_intent="Test",
            execution_graph=[
                ExecutionStep(
                    step_id=1,
                    task="Confirm port 8080 on localhost is open.",
                    prompt_template_id="default",
                    assigned_model="test",
                ),
            ],
        )

        with patch("src.planweaver.scout.run_probe", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("Probe failed")

            report = await scout.scout_plan(plan)

            assert len(report.preconditions) == 1
            assert report.preconditions[0].probe_error == "Probe failed"

    @pytest.mark.asyncio
    async def test_scout_plan_unverifiable_unknown_type(self, scout):
        from src.planweaver.probes.base import ProbeResult

        plan = Plan(
            session_id="test-123",
            user_intent="Test",
            execution_graph=[
                ExecutionStep(
                    step_id=1,
                    task="Confirm port 9090 on localhost is open.",
                    prompt_template_id="default",
                    assigned_model="test",
                ),
            ],
        )

        with patch("src.planweaver.scout.run_probe", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ProbeResult(
                success=False, result=None, error="Unknown precondition type: unknown"
            )

            report = await scout.scout_plan(plan)

            assert len(report.unverifiable) == 1
