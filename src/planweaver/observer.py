"""
Observer support for adaptive execution.

The Observer inspects completed execution steps and raises a structured
re-planning signal when the output appears inconsistent with downstream
expectations.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .models.plan import ExecutionStep, Plan


class ObservationResult(BaseModel):
    step_id: int
    expected_output_schema: dict[str, Any]
    actual_output: Any
    drift_detected: bool
    drift_description: str | None = None
    recommended_action: Literal["continue", "retry_step", "replan_from_here", "abort"] = "continue"
    affected_step_ids: list[int] = Field(default_factory=list)
    confidence: float = 0.0


class Observer:
    """
    Lightweight execution observer.

    This first-pass implementation uses deterministic heuristics so the
    adaptive execution loop can ship without introducing another LLM call
    on the critical path.
    """

    _ERROR_KEYWORDS = (
        "error",
        "failed",
        "failure",
        "exception",
        "traceback",
        "unable",
        "cannot",
        "can't",
        "not found",
        "timed out",
        "timeout",
    )

    async def on_step_complete(self, step: ExecutionStep, plan: Plan) -> ObservationResult:
        confidence = 0.0
        description: str | None = None

        if self._is_empty_output(step.output):
            confidence = 0.98
            description = "The step completed but returned no usable output."
        elif isinstance(step.output, str):
            output_lower = step.output.lower()
            if any(keyword in output_lower for keyword in self._ERROR_KEYWORDS):
                confidence = 0.92
                description = "The step output contains failure-like language despite reporting success."

        drift_detected = confidence > 0.0
        recommended_action: Literal["continue", "retry_step", "replan_from_here", "abort"]
        if drift_detected:
            recommended_action = "replan_from_here"
        else:
            recommended_action = "continue"

        return ObservationResult(
            step_id=step.step_id,
            expected_output_schema=self._expected_output_schema(step),
            actual_output=step.output,
            drift_detected=drift_detected,
            drift_description=description,
            recommended_action=recommended_action,
            affected_step_ids=self._affected_step_ids(step.step_id, plan),
            confidence=confidence,
        )

    async def synthesise_replan_message(self, findings: list[ObservationResult]) -> str:
        if not findings:
            return "Observer did not detect execution drift."

        finding = findings[0]
        affected = ", ".join(str(step_id) for step_id in finding.affected_step_ids) or "none"
        return (
            f"Observer detected drift after step {finding.step_id}. "
            f"{finding.drift_description or 'Output was inconsistent with downstream needs.'} "
            f"Affected steps: {affected}."
        )

    def _expected_output_schema(self, step: ExecutionStep) -> dict[str, Any]:
        return {
            "type": "non_empty_result",
            "step_id": step.step_id,
            "task": step.task,
            "dependencies": list(step.dependencies),
        }

    def _affected_step_ids(self, step_id: int, plan: Plan) -> list[int]:
        affected = {step_id}
        changed = True
        while changed:
            changed = False
            for candidate in plan.execution_graph:
                if candidate.step_id in affected:
                    continue
                if any(dependency in affected for dependency in candidate.dependencies):
                    affected.add(candidate.step_id)
                    changed = True
        return sorted(affected)

    def _is_empty_output(self, output: Any) -> bool:
        if output is None:
            return True
        if isinstance(output, str):
            return not output.strip()
        if isinstance(output, (list, dict, tuple, set)):
            return len(output) == 0
        return False
