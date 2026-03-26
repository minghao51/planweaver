import pytest
from src.planweaver.observer import Observer, ObservationResult
from src.planweaver.models.plan import ExecutionStep, Plan


class TestObserverDriftDetection:
    """Tests for Observer drift detection heuristics."""

    @pytest.fixture
    def observer(self):
        return Observer()

    @pytest.fixture
    def simple_plan(self):
        return Plan(
            session_id="test-123",
            user_intent="Build a web scraper",
        )

    @pytest.mark.asyncio
    async def test_detects_empty_string_output(self, observer, simple_plan):
        step = ExecutionStep(
            step_id=1,
            task="Set up project",
            prompt_template_id="default",
            assigned_model="test",
            output="",
        )
        simple_plan.execution_graph = [step]

        result = await observer.on_step_complete(step, simple_plan)

        assert result.drift_detected is True
        assert result.confidence == 0.98
        assert "no usable output" in result.drift_description.lower()
        assert result.recommended_action == "replan_from_here"

    @pytest.mark.asyncio
    async def test_detects_empty_list_output(self, observer, simple_plan):
        step = ExecutionStep(
            step_id=1,
            task="Fetch items",
            prompt_template_id="default",
            assigned_model="test",
            output=[],
        )
        simple_plan.execution_graph = [step]

        result = await observer.on_step_complete(step, simple_plan)

        assert result.drift_detected is True
        assert result.confidence == 0.98

    @pytest.mark.asyncio
    async def test_detects_empty_dict_output(self, observer, simple_plan):
        step = ExecutionStep(
            step_id=1,
            task="Get config",
            prompt_template_id="default",
            assigned_model="test",
            output={},
        )
        simple_plan.execution_graph = [step]

        result = await observer.on_step_complete(step, simple_plan)

        assert result.drift_detected is True

    @pytest.mark.asyncio
    async def test_detects_error_keyword_in_output(self, observer, simple_plan):
        step = ExecutionStep(
            step_id=1,
            task="Run command",
            prompt_template_id="default",
            assigned_model="test",
            output="Command failed with error: file not found",
        )
        simple_plan.execution_graph = [step]

        result = await observer.on_step_complete(step, simple_plan)

        assert result.drift_detected is True
        assert result.confidence == 0.92
        assert "failure-like language" in result.drift_description.lower()

    @pytest.mark.asyncio
    async def test_detects_exception_keyword(self, observer, simple_plan):
        step = ExecutionStep(
            step_id=1,
            task="Process",
            prompt_template_id="default",
            assigned_model="test",
            output="Exception occurred during processing",
        )
        simple_plan.execution_graph = [step]

        result = await observer.on_step_complete(step, simple_plan)

        assert result.drift_detected is True

    @pytest.mark.asyncio
    async def test_detects_timeout_keywords(self, observer, simple_plan):
        step = ExecutionStep(
            step_id=1,
            task="API call",
            prompt_template_id="default",
            assigned_model="test",
            output="Request timed out after 30 seconds",
        )
        simple_plan.execution_graph = [step]

        result = await observer.on_step_complete(step, simple_plan)

        assert result.drift_detected is True

    @pytest.mark.asyncio
    async def test_no_drift_for_valid_output(self, observer, simple_plan):
        step = ExecutionStep(
            step_id=1,
            task="Process",
            prompt_template_id="default",
            assigned_model="test",
            output="Successfully processed 150 items",
        )
        simple_plan.execution_graph = [step]

        result = await observer.on_step_complete(step, simple_plan)

        assert result.drift_detected is False
        assert result.confidence == 0.0
        assert result.recommended_action == "continue"

    @pytest.mark.asyncio
    async def test_none_output_detected_as_empty(self, observer, simple_plan):
        step = ExecutionStep(
            step_id=1,
            task="Check status",
            prompt_template_id="default",
            assigned_model="test",
            output=None,
        )
        simple_plan.execution_graph = [step]

        result = await observer.on_step_complete(step, simple_plan)

        assert result.drift_detected is True

    @pytest.mark.asyncio
    async def test_whitespace_only_string_detected_as_empty(self, observer, simple_plan):
        step = ExecutionStep(
            step_id=1,
            task="Get result",
            prompt_template_id="default",
            assigned_model="test",
            output="   \n\t  ",
        )
        simple_plan.execution_graph = [step]

        result = await observer.on_step_complete(step, simple_plan)

        assert result.drift_detected is True


class TestObserverAffectedSteps:
    """Tests for Observer affected steps cascade calculation."""

    @pytest.fixture
    def observer(self):
        return Observer()

    def test_single_step_with_no_dependencies(self, observer):
        plan = Plan(
            session_id="test-123",
            user_intent="Test",
        )
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="Step 1",
                prompt_template_id="default",
                assigned_model="test",
            ),
        ]

        affected = observer._affected_step_ids(1, plan)

        assert affected == [1]

    def test_cascade_through_direct_dependency(self, observer):
        plan = Plan(
            session_id="test-123",
            user_intent="Test",
        )
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="Step 1",
                prompt_template_id="default",
                assigned_model="test",
            ),
            ExecutionStep(
                step_id=2,
                task="Step 2",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[1],
            ),
        ]

        affected = observer._affected_step_ids(1, plan)

        assert set(affected) == {1, 2}

    def test_cascade_through_multiple_levels(self, observer):
        plan = Plan(
            session_id="test-123",
            user_intent="Test",
        )
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="Step 1",
                prompt_template_id="default",
                assigned_model="test",
            ),
            ExecutionStep(
                step_id=2,
                task="Step 2",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[1],
            ),
            ExecutionStep(
                step_id=3,
                task="Step 3",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[2],
            ),
        ]

        affected = observer._affected_step_ids(1, plan)

        assert set(affected) == {1, 2, 3}

    def test_cascade_through_multiple_paths(self, observer):
        plan = Plan(
            session_id="test-123",
            user_intent="Test",
        )
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="Step 1",
                prompt_template_id="default",
                assigned_model="test",
            ),
            ExecutionStep(
                step_id=2,
                task="Step 2",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[1],
            ),
            ExecutionStep(
                step_id=3,
                task="Step 3",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[1],
            ),
            ExecutionStep(
                step_id=4,
                task="Step 4",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[2, 3],
            ),
        ]

        affected = observer._affected_step_ids(1, plan)

        assert set(affected) == {1, 2, 3, 4}

    def test_diamond_dependency_cascade(self, observer):
        plan = Plan(
            session_id="test-123",
            user_intent="Test",
        )
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="Root",
                prompt_template_id="default",
                assigned_model="test",
            ),
            ExecutionStep(
                step_id=2,
                task="Branch A",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[1],
            ),
            ExecutionStep(
                step_id=3,
                task="Branch B",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[1],
            ),
            ExecutionStep(
                step_id=4,
                task="Merge",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[2, 3],
            ),
        ]

        affected = observer._affected_step_ids(1, plan)

        assert set(affected) == {1, 2, 3, 4}

    def test_unaffected_step_not_in_cascade(self, observer):
        plan = Plan(
            session_id="test-123",
            user_intent="Test",
        )
        plan.execution_graph = [
            ExecutionStep(
                step_id=1,
                task="Failed step",
                prompt_template_id="default",
                assigned_model="test",
            ),
            ExecutionStep(
                step_id=2,
                task="Dependent step",
                prompt_template_id="default",
                assigned_model="test",
                dependencies=[1],
            ),
            ExecutionStep(
                step_id=3,
                task="Independent step",
                prompt_template_id="default",
                assigned_model="test",
            ),
        ]

        affected = observer._affected_step_ids(1, plan)

        assert 3 not in affected
        assert set(affected) == {1, 2}


class TestObserverReplanMessage:
    """Tests for Observer replan message synthesis."""

    @pytest.fixture
    def observer(self):
        return Observer()

    @pytest.mark.asyncio
    async def test_synthesizes_message_from_empty_findings(self, observer):
        result = await observer.synthesise_replan_message([])

        assert result == "Observer did not detect execution drift."

    @pytest.mark.asyncio
    async def test_synthesizes_message_with_affected_steps(self, observer):
        findings = [
            ObservationResult(
                step_id=2,
                expected_output_schema={},
                actual_output="",
                drift_detected=True,
                drift_description="Output was empty",
                recommended_action="replan_from_here",
                affected_step_ids=[2, 3, 4],
                confidence=0.98,
            )
        ]

        result = await observer.synthesise_replan_message(findings)

        assert "step 2" in result
        assert "Output was empty" in result
        assert "2, 3, 4" in result

    @pytest.mark.asyncio
    async def test_synthesizes_message_no_affected_steps(self, observer):
        findings = [
            ObservationResult(
                step_id=1,
                expected_output_schema={},
                actual_output="",
                drift_detected=True,
                drift_description="Nothing produced",
                recommended_action="replan_from_here",
                affected_step_ids=[],
                confidence=0.98,
            )
        ]

        result = await observer.synthesise_replan_message(findings)

        assert "none" in result


class TestObserverExpectedOutputSchema:
    """Tests for Observer expected output schema generation."""

    @pytest.fixture
    def observer(self):
        return Observer()

    def test_includes_step_id_and_task(self, observer):
        step = ExecutionStep(
            step_id=5,
            task="Run tests",
            prompt_template_id="default",
            assigned_model="test",
            dependencies=[1, 2],
        )

        schema = observer._expected_output_schema(step)

        assert schema["step_id"] == 5
        assert schema["task"] == "Run tests"
        assert schema["type"] == "non_empty_result"
        assert set(schema["dependencies"]) == {1, 2}


class TestObserverEdgeCases:
    """Tests for Observer edge cases."""

    @pytest.fixture
    def observer(self):
        return Observer()

    def test_empty_output_detection_for_tuple(self, observer):
        assert observer._is_empty_output(()) is True

    def test_empty_output_detection_for_set(self, observer):
        assert observer._is_empty_output(set()) is True

    def test_non_empty_list_passes(self, observer):
        assert observer._is_empty_output([None]) is False
        assert observer._is_empty_output(["item"]) is False

    def test_non_empty_dict_passes(self, observer):
        assert observer._is_empty_output({"key": None}) is False

    def test_non_empty_string_passes(self, observer):
        assert observer._is_empty_output("x") is False
        assert observer._is_empty_output("0") is False
        assert observer._is_empty_output("false") is False

    @pytest.mark.asyncio
    async def test_observation_result_fields_complete(self, observer):
        plan = Plan(session_id="test-123", user_intent="Test")
        step = ExecutionStep(
            step_id=1,
            task="Test",
            prompt_template_id="default",
            assigned_model="test",
            output="error occurred",
        )
        plan.execution_graph = [step]

        result = await observer.on_step_complete(step, plan)

        assert result.step_id == 1
        assert result.expected_output_schema["type"] == "non_empty_result"
        assert result.actual_output == "error occurred"
        assert len(result.affected_step_ids) == 1
