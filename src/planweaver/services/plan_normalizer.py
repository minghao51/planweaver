from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional

from ..models.plan import (
    ManualPlanSubmission,
    NormalizedPlan,
    NormalizedStep,
    PlanSourceType,
)


class PlanNormalizer:
    """Convert planner, variant, and manual inputs into a canonical plan shape."""

    def normalize_manual_plan(self, submission: ManualPlanSubmission) -> NormalizedPlan:
        warnings: List[str] = []
        steps = submission.steps or self._steps_from_text(submission.plan_text or "")

        if not steps:
            warnings.append("No structured steps provided; added a placeholder step.")
            steps = [
                NormalizedStep(
                    step_id="step-1",
                    description="Refine the manual plan into executable steps.",
                    validation=["Confirm execution steps with the user."],
                )
            ]

        if not submission.success_criteria:
            warnings.append("Missing explicit success criteria.")

        if not any(step.validation for step in steps):
            warnings.append(
                "No step-level validation found; added a default verification."
            )
            steps[-1].validation.append(
                "Verify the outcome against the requested goal."
            )

        return NormalizedPlan(
            session_id=submission.session_id,
            source_type=PlanSourceType.MANUAL,
            source_model="human",
            planning_style="manual",
            title=submission.title,
            summary=submission.summary or submission.plan_text or submission.title,
            assumptions=submission.assumptions,
            constraints=submission.constraints,
            success_criteria=submission.success_criteria,
            risks=submission.risks,
            fallbacks=submission.fallbacks,
            estimated_time_minutes=submission.estimated_time_minutes,
            estimated_cost_usd=submission.estimated_cost_usd,
            steps=steps,
            metadata=submission.metadata,
            normalization_warnings=warnings,
        )

    def normalize_generated_plan(
        self,
        plan_data: Dict[str, Any],
        *,
        session_id: Optional[str] = None,
        source_type: PlanSourceType = PlanSourceType.LLM_GENERATED,
        source_model: str = "unknown",
        planning_style: str = "baseline",
    ) -> NormalizedPlan:
        warnings: List[str] = []
        title = plan_data.get("title") or "Untitled plan"
        summary = (
            plan_data.get("summary")
            or plan_data.get("description")
            or plan_data.get("approach")
            or title
        )

        steps = self._normalize_steps(
            plan_data.get("steps") or plan_data.get("execution_graph")
        )
        if not steps:
            warnings.append(
                "No executable steps were provided; added a placeholder step."
            )
            steps = [
                NormalizedStep(
                    step_id="step-1",
                    description="Decompose the plan into executable steps.",
                    validation=["Review the generated decomposition."],
                )
            ]

        success_criteria = self._listify(plan_data.get("success_criteria"))
        if not success_criteria:
            warnings.append("Missing explicit success criteria.")

        if not any(step.validation for step in steps):
            warnings.append(
                "No step-level validation found; added a default verification."
            )
            steps[-1].validation.append(
                "Verify the final output satisfies the user intent."
            )

        estimated_cost = self._to_decimal(plan_data.get("estimated_cost_usd"))

        plan_id = (
            plan_data.get("id")
            or plan_data.get("proposal_id")
            or plan_data.get("plan_id")
        )

        normalized = NormalizedPlan(
            session_id=session_id or plan_data.get("session_id"),
            source_type=source_type,
            source_model=source_model,
            planning_style=planning_style,
            title=title,
            summary=summary,
            assumptions=self._listify(plan_data.get("assumptions")),
            constraints=self._constraints_to_list(plan_data.get("constraints")),
            success_criteria=success_criteria,
            risks=self._listify(
                plan_data.get("risks") or plan_data.get("risk_factors")
            ),
            fallbacks=self._listify(plan_data.get("fallbacks")),
            estimated_time_minutes=self._safe_int(
                plan_data.get("estimated_time_minutes")
            ),
            estimated_cost_usd=estimated_cost,
            steps=steps,
            metadata=dict(plan_data.get("metadata") or {}),
            normalization_warnings=warnings,
        )
        if plan_id:
            normalized.id = str(plan_id)
        return normalized

    def _normalize_steps(self, raw_steps: Any) -> List[NormalizedStep]:
        if not isinstance(raw_steps, Iterable) or isinstance(
            raw_steps, (str, bytes, dict)
        ):
            return []

        normalized_steps: List[NormalizedStep] = []
        for index, step in enumerate(raw_steps, start=1):
            if not isinstance(step, dict):
                continue

            description = step.get("description") or step.get("task")
            if not description:
                continue

            normalized_steps.append(
                NormalizedStep(
                    step_id=str(step.get("step_id") or f"step-{index}"),
                    description=description,
                    dependencies=[str(dep) for dep in step.get("dependencies", [])],
                    validation=self._listify(
                        step.get("validation") or step.get("checks")
                    ),
                    tools=self._listify(step.get("tools")),
                    owner_model=step.get("owner_model") or step.get("assigned_model"),
                    estimated_time_minutes=self._safe_int(
                        step.get("estimated_time_minutes")
                    ),
                )
            )
        return normalized_steps

    def _steps_from_text(self, plan_text: str) -> List[NormalizedStep]:
        lines = [line.strip(" -\t") for line in plan_text.splitlines() if line.strip()]
        return [
            NormalizedStep(step_id=f"step-{index}", description=line)
            for index, line in enumerate(lines, start=1)
        ]

    def _listify(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, Iterable):
            result = []
            for item in value:
                text = str(item).strip()
                if text:
                    result.append(text)
            return result
        text = str(value).strip()
        return [text] if text else []

    def _constraints_to_list(self, constraints: Any) -> List[str]:
        if isinstance(constraints, dict):
            return [f"{key}: {value}" for key, value in constraints.items()]
        return self._listify(constraints)

    def _safe_int(self, value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
