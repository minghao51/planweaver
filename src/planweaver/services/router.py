from typing import Dict, Any, Optional, List
import time
import logging
from datetime import datetime, timezone

from ..models.plan import Plan, ExecutionStep, StepStatus, PlanStatus
from .llm_gateway import LLMGateway
from .template_engine import TemplateEngine

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0


class ExecutionRouter:
    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        template_engine: Optional[TemplateEngine] = None
    ):
        self.llm = llm_gateway or LLMGateway()
        self.template_engine = template_engine or TemplateEngine()

    def get_executable_steps(self, plan: Plan) -> List[ExecutionStep]:
        pending = [s for s in plan.execution_graph if s.status == StepStatus.PENDING]
        completed_ids = {s.step_id for s in plan.execution_graph if s.status == StepStatus.COMPLETED}

        executable = []
        for step in pending:
            if all(dep in completed_ids for dep in step.dependencies):
                executable.append(step)

        return executable

    def _build_step_prompt(
        self,
        step: ExecutionStep,
        plan: Plan,
        context: Dict[str, Any],
    ) -> str:
        return self.template_engine.render_executor_prompt(
            scenario_name=plan.scenario_name or "",
            step_task=step.task,
            context={
                **context,
                "locked_constraints": plan.locked_constraints,
                "previous_outputs": self._get_previous_outputs(plan, step),
            },
        )

    def _mark_step_started(self, step: ExecutionStep) -> None:
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.now(timezone.utc)

    def _mark_step_completed(self, step: ExecutionStep, output: Any) -> None:
        step.completed_at = datetime.now(timezone.utc)
        step.output = output
        step.status = StepStatus.COMPLETED

    def _mark_step_failed(self, step: ExecutionStep, error: str) -> None:
        step.status = StepStatus.FAILED
        step.error = error

    def _call_model(self, model: str, prompt: str) -> Dict[str, Any]:
        return self.llm.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
        )

    def _execute_with_retries(
        self,
        step: ExecutionStep,
        actual_model: str,
        prompt: str,
    ) -> Dict[str, Any]:
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self._call_model(actual_model, prompt)
                if response:
                    self._mark_step_completed(step, response.get("content"))
                    return {
                        "step_id": step.step_id,
                        "output": step.output,
                        "model": actual_model,
                        "success": True,
                    }
                last_error = "Empty response"
            except Exception as exc:
                last_error = str(exc)
                logger.warning(f"Step {step.step_id} attempt {attempt + 1} failed: {exc}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_BASE * (2 ** attempt))

        error_message = f"Failed after {MAX_RETRIES} attempts: {last_error}"
        self._mark_step_failed(step, error_message)
        return {
            "step_id": step.step_id,
            "error": step.error,
            "model": actual_model,
            "success": False,
        }

    def _validate_execution_graph(self, plan: Plan) -> None:
        steps_by_id = {step.step_id: step for step in plan.execution_graph}
        if len(steps_by_id) != len(plan.execution_graph):
            raise ValueError("Execution graph contains duplicate step_id values")

        for step in plan.execution_graph:
            for dep in step.dependencies:
                if dep == step.step_id:
                    raise ValueError(f"Step {step.step_id} cannot depend on itself")
                if dep not in steps_by_id:
                    raise ValueError(
                        f"Step {step.step_id} depends on missing step {dep}"
                    )

        visiting: set[int] = set()
        visited: set[int] = set()

        def visit(step_id: int) -> None:
            if step_id in visited:
                return
            if step_id in visiting:
                raise ValueError(f"Execution graph contains a dependency cycle at step {step_id}")

            visiting.add(step_id)
            for dep_id in steps_by_id[step_id].dependencies:
                visit(dep_id)
            visiting.remove(step_id)
            visited.add(step_id)

        for step_id in steps_by_id:
            visit(step_id)

    def execute_step(
        self,
        step: ExecutionStep,
        plan: Plan,
        context: Dict[str, Any],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        actual_model = model or step.assigned_model

        prompt = self._build_step_prompt(step, plan, context)
        self._mark_step_started(step)
        return self._execute_with_retries(step, actual_model, prompt)

    def _get_previous_outputs(self, plan: Plan, current_step: ExecutionStep) -> Dict[int, Any]:
        outputs = {}
        for step in plan.execution_graph:
            if step.status == StepStatus.COMPLETED and step.step_id in current_step.dependencies:
                outputs[step.step_id] = step.output
        return outputs

    def execute_plan(
        self,
        plan: Plan,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 100
    ) -> Plan:
        if context is None:
            context = {}

        self._validate_execution_graph(plan)
        plan.status = PlanStatus.EXECUTING
        step_count = 0

        while step_count < max_steps:
            executable_steps = self.get_executable_steps(plan)

            if not executable_steps:
                break

            for step in executable_steps:
                result = self.execute_step(step, plan, context)
                step_count += 1

                if not result["success"]:
                    plan.status = PlanStatus.FAILED
                    return plan

            if not self.get_executable_steps(plan):
                break

        all_completed = all(
            s.status == StepStatus.COMPLETED or s.status == StepStatus.SKIPPED
            for s in plan.execution_graph
        )

        if all_completed:
            plan.status = PlanStatus.COMPLETED
            plan.final_output = self._aggregate_outputs(plan)
        else:
            plan.status = PlanStatus.FAILED

        return plan

    def _aggregate_outputs(self, plan: Plan) -> Dict[str, Any]:
        outputs = {}
        for step in plan.execution_graph:
            if step.output:
                outputs[f"step_{step.step_id}"] = step.output
        return outputs
