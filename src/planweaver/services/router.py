from typing import Dict, Any, Optional, List
import time
import logging
from datetime import datetime

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

    def execute_step(
        self,
        step: ExecutionStep,
        plan: Plan,
        context: Dict[str, Any],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        actual_model = model or step.assigned_model

        prompt = self.template_engine.render_executor_prompt(
            scenario_name=plan.scenario_name or "",
            step_task=step.task,
            context={
                **context,
                "locked_constraints": plan.locked_constraints,
                "previous_outputs": self._get_previous_outputs(plan, step)
            }
        )

        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.utcnow()

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.llm.complete(
                    model=actual_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=8192
                )

                step.completed_at = datetime.utcnow()

                if response:
                    step.output = response["content"]
                    step.status = StepStatus.COMPLETED
                    return {
                        "step_id": step.step_id,
                        "output": step.output,
                        "model": actual_model,
                        "success": True
                    }
                last_error = "Empty response"
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Step {step.step_id} attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_BASE * (2 ** attempt))

        step.status = StepStatus.FAILED
        step.error = f"Failed after {MAX_RETRIES} attempts: {last_error}"
        return {
            "step_id": step.step_id,
            "error": step.error,
            "model": actual_model,
            "success": False
        }

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

    def can_skip_step(self, step: ExecutionStep, context: Dict[str, Any]) -> bool:
        return False
