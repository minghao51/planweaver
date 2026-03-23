"""
PreconditionScout - Scout agent for assumption validation.

The Scout identifies steps with unverified preconditions and validates them
before the plan reaches execution. This catches empirical flaws about the
state of the world that the Critic cannot find.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional
from dataclasses import dataclass

from planweaver.models.plan import Plan, ExecutionStep, PreconditionAnnotation
from planweaver.probes import run_probe, PRECONDITION_TYPE_TO_PROBE


PRECONDITION_PATTERNS = [
    (re.compile(r"file [`'\"](.+?)[`'\"] exists", re.IGNORECASE), "file_exists"),
    (re.compile(r"(`|)(.+?)(`) exists", re.IGNORECASE), "file_exists"),
    (re.compile(r"API [`'\"](.+?)[`'\"] is reachable", re.IGNORECASE), "api_reachable"),
    (re.compile(r"(`|)(https?://[^\s`'\"]+)(`) is reachable", re.IGNORECASE), "api_reachable"),
    (re.compile(r"import [`'\"](.+?)[`'\"] available", re.IGNORECASE), "import_available"),
    (re.compile(r"(`|)([a-zA-Z_][a-zA-Z0-9_.]+)(`) is installed", re.IGNORECASE), "import_available"),
    (re.compile(r"env [`'\"](.+?)[`'\"] is set", re.IGNORECASE), "env_var_set"),
    (re.compile(r"\$([A-Z_][A-Z0-9_]*) is set", re.IGNORECASE), "env_var_set"),
    (re.compile(r"service [`'\"](.+?)[`'\"] is running", re.IGNORECASE), "service_running"),
    (re.compile(r"port [:digit:]+ on (.+?) is open", re.IGNORECASE), "service_running"),
]

ASSUMPTION_KEYWORDS = [
    "assume",
    "expects",
    "requires",
    "needs",
    "must have",
    "should have",
    "precondition",
]


@dataclass
class IdentifiedPrecondition:
    step_id: int
    precondition_type: str
    check_expression: str
    original_text: str


class PreconditionScout:
    """
    Identifies and validates preconditions in execution steps.

    The scout:
    1. Extracts potential preconditions from step task descriptions
    2. Runs lightweight probes to validate them
    3. Annotates steps with validation results
    """

    def __init__(self):
        self._precondition_types = list(PRECONDITION_TYPE_TO_PROBE.keys())

    async def scout_plan(self, plan: Plan) -> ScoutReport:
        """
        Scout a plan's execution graph for unverified preconditions.

        Returns a ScoutReport with identified, failed, and unverifiable preconditions.
        """
        identified = self._identify_preconditions(plan.execution_graph)

        if not identified:
            return ScoutReport(
                preconditions=[],
                failed=[],
                unverifiable=[],
            )

        probed = await asyncio.gather(
            *[self._probe_precondition(p) for p in identified],
            return_exceptions=True,
        )

        preconditions: list[PreconditionResult] = []
        failed: list[PreconditionResult] = []
        unverifiable: list[PreconditionResult] = []

        for p, result in zip(identified, probed):
            if isinstance(result, Exception):
                pr = PreconditionResult(
                    step_id=p.step_id,
                    precondition_type=p.precondition_type,
                    check_expression=p.check_expression,
                    probe_result=None,
                    probe_error=str(result),
                )
            else:
                probe_result: Optional[bool] = result.result  # type: ignore[union-attr]
                probe_error: Optional[str] = result.error  # type: ignore[union-attr]
                pr = PreconditionResult(
                    step_id=p.step_id,
                    precondition_type=p.precondition_type,
                    check_expression=p.check_expression,
                    probe_result=probe_result,
                    probe_error=probe_error,
                )
                if probe_result is False:
                    failed.append(pr)
                elif probe_error and "Unknown precondition type" in probe_error:
                    unverifiable.append(pr)

            preconditions.append(pr)

        return ScoutReport(
            preconditions=preconditions,
            failed=failed,
            unverifiable=unverifiable,
        )

    def annotate_plan(self, plan: Plan, report: ScoutReport) -> Plan:
        """
        Annotate the plan's execution steps with precondition results.
        """
        result_map: dict[int, list[PreconditionResult]] = {}
        for pr in report.preconditions:
            if pr.step_id not in result_map:
                result_map[pr.step_id] = []
            result_map[pr.step_id].append(pr)

        for step in plan.execution_graph:
            if step.step_id in result_map:
                step.preconditions = [
                    PreconditionAnnotation(
                        precondition_type=pr.precondition_type,
                        check_expression=pr.check_expression,
                        probe_result=pr.probe_result,
                        probe_error=pr.probe_error,
                    )
                    for pr in result_map[step.step_id]
                ]

        return plan

    def _identify_preconditions(self, steps: list[ExecutionStep]) -> list[IdentifiedPrecondition]:
        """Extract potential preconditions from step task descriptions."""
        identified = []

        for step in steps:
            step_preconditions = self._extract_step_preconditions(step.task)
            for ptype, expr, original in step_preconditions:
                identified.append(
                    IdentifiedPrecondition(
                        step_id=step.step_id,
                        precondition_type=ptype,
                        check_expression=expr,
                        original_text=original,
                    )
                )

        return identified

    def _extract_step_preconditions(self, task: str) -> list[tuple[str, str, str]]:
        """Extract precondition-like statements from task text."""
        results = []

        for pattern, ptype in PRECONDITION_PATTERNS:
            for match in pattern.finditer(task):
                expr = (match.group(2) or match.group(1)).strip()
                if expr and len(expr) > 1:
                    results.append((ptype, expr, match.group(0)))

        if not results and any(kw in task.lower() for kw in ASSUMPTION_KEYWORDS):
            if "file" in task.lower():
                file_match = re.search(r"([a-zA-Z0-9_./\-]+)", task)
                if file_match:
                    results.append(("file_exists", file_match.group(1), task))

        return results

    async def _probe_precondition(self, precondition: IdentifiedPrecondition) -> ScoutProbeResult:
        """Run the appropriate probe for a precondition."""
        result = await run_probe(precondition.precondition_type, precondition.check_expression)
        return ScoutProbeResult(
            success=result.success,
            result=result.result,
            error=result.error,
        )


@dataclass
class ScoutProbeResult:
    success: bool
    result: Optional[bool]
    error: Optional[str] = None


@dataclass
class PreconditionResult:
    step_id: int
    precondition_type: str
    check_expression: str
    probe_result: Optional[bool]
    probe_error: Optional[str]


@dataclass
class ScoutReport:
    preconditions: list[PreconditionResult]
    failed: list[PreconditionResult]
    unverifiable: list[PreconditionResult]

    def has_failed_preconditions(self) -> bool:
        return len(self.failed) > 0

    def format_failed_message(self) -> str:
        if not self.failed:
            return ""
        lines = ["Precondition validation failed:"]
        for p in self.failed:
            lines.append(
                f"  Step {p.step_id}: {p.precondition_type} check '{p.check_expression}'"
                f" returned False"
                + (f" (error: {p.probe_error})" if p.probe_error else "")
            )
        return "\n".join(lines)
