from src.planweaver.models.plan import ExecutionStep
from src.planweaver.scout import PreconditionScout


def test_extracts_service_precondition_from_port_format():
    scout = PreconditionScout()

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
