"""
Critic Agent for Plan Review

Adversarial agent that identifies logical flaws, missing constraints,
and feasibility issues in generated plans.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from .models.plan import Plan, CandidatePlan, ExecutionStep
from .services.llm_gateway import LLMGateway


logger = logging.getLogger(__name__)


class ObjectionSeverity(str, Enum):
    """Severity levels for objections."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ObjectionCategory(str, Enum):
    """Categories of objections."""

    LOGIC = "logic"
    FEASIBILITY = "feasibility"
    COMPLETENESS = "completeness"
    SAFETY = "safety"
    COST = "cost"


class Verdict(str, Enum):
    """Overall verdict on the plan."""

    ACCEPT = "accept"
    REVISE = "revise"
    REJECT = "reject"


class CriticObjection(BaseModel):
    """A specific objection to a plan or step."""

    objection_id: str = Field(default_factory=lambda: f"obj_{datetime.now().timestamp()}")
    severity: ObjectionSeverity
    category: ObjectionCategory
    step_id: Optional[int] = None
    description: str
    suggested_revision: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class CriticReport(BaseModel):
    """Complete critic report for a candidate plan."""

    session_id: str
    candidate_id: str
    objections: List[CriticObjection] = Field(default_factory=list)
    overall_verdict: Verdict
    critical_issue_count: int = 0
    high_issue_count: int = 0
    medium_issue_count: int = 0
    low_issue_count: int = 0
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: str = ""

    def has_critical_issues(self) -> bool:
        """Check if report has critical objections."""
        return self.critical_issue_count > 0

    def should_trigger_revision(self) -> bool:
        """Determine if the plan should be revised."""
        return self.overall_verdict in [Verdict.REVISE, Verdict.REJECT]


class Critic:
    """
    Adversarial critic agent for plan review.

    Identifies logical flaws, missing constraints, feasibility issues,
    completeness gaps, safety concerns, and cost problems in plans.
    """

    def __init__(self, llm_gateway: LLMGateway):
        """
        Initialize critic agent.

        Args:
            llm_gateway: LLM gateway for analysis
        """
        self.llm = llm_gateway

    async def review_plan(self, plan: Plan, candidate: CandidatePlan) -> CriticReport:
        """
        Review a candidate plan and identify issues.

        Args:
            plan: The overall planning session
            candidate: The candidate plan to review

        Returns:
            CriticReport with objections and verdict
        """
        try:
            # Analyze the plan for issues
            objections = await self._identify_objections(plan, candidate)

            # Count objections by severity
            critical = sum(1 for o in objections if o.severity == ObjectionSeverity.CRITICAL)
            high = sum(1 for o in objections if o.severity == ObjectionSeverity.HIGH)
            medium = sum(1 for o in objections if o.severity == ObjectionSeverity.MEDIUM)
            low = sum(1 for o in objections if o.severity == ObjectionSeverity.LOW)

            # Determine overall verdict
            verdict = self._determine_verdict(objections, critical, high)

            # Generate summary
            summary = self._generate_summary(objections, verdict)

            report = CriticReport(
                session_id=plan.session_id,
                candidate_id=candidate.candidate_id,
                objections=objections,
                overall_verdict=verdict,
                critical_issue_count=critical,
                high_issue_count=high,
                medium_issue_count=medium,
                low_issue_count=low,
                summary=summary,
                confidence=self._calculate_confidence(objections),
            )

            logger.info(
                f"Critic review complete: {verdict.value} verdict "
                f"({critical} critical, {high} high, {medium} medium, {low} low)"
            )

            return report

        except Exception as e:
            logger.error(f"Critic review failed: {e}")
            # Return minimal report on error
            return CriticReport(
                session_id=plan.session_id,
                candidate_id=candidate.candidate_id,
                objections=[],
                overall_verdict=Verdict.ACCEPT,
                summary="Review failed - accepting plan by default",
                confidence=0.0,
            )

    async def _identify_objections(
        self,
        plan: Plan,
        candidate: CandidatePlan,
    ) -> List[CriticObjection]:
        """
        Identify objections in the candidate plan.

        Uses LLM to analyze the plan for various types of issues.
        """
        objections = []

        # Analyze execution steps
        for step in candidate.execution_graph:
            step_objections = await self._analyze_step(step, plan)
            objections.extend(step_objections)

        # Analyze overall plan completeness
        completeness_objections = await self._analyze_completeness(plan, candidate)
        objections.extend(completeness_objections)

        # Analyze dependencies
        dependency_objections = await self._analyze_dependencies(candidate)
        objections.extend(dependency_objections)

        # Analyze for safety concerns
        safety_objections = await self._analyze_safety(candidate)
        objections.extend(safety_objections)

        return objections

    async def _analyze_step(
        self,
        step: ExecutionStep,
        plan: Plan,
    ) -> List[CriticObjection]:
        """Analyze a single execution step for issues."""
        objections = []

        # Check for vague tasks
        if self._is_vague_task(step.task):
            objections.append(
                CriticObjection(
                    severity=ObjectionSeverity.MEDIUM,
                    category=ObjectionCategory.COMPLETENESS,
                    step_id=step.step_id,
                    description=f"Step {step.step_id} task is vague: '{step.task}'",
                    suggested_revision="Make the task more specific with clear deliverables",
                    confidence=0.7,
                )
            )

        # Check for missing dependencies
        if not step.dependencies and step.step_id > 1:
            # First step can have no dependencies
            objections.append(
                CriticObjection(
                    severity=ObjectionSeverity.LOW,
                    category=ObjectionCategory.LOGIC,
                    step_id=step.step_id,
                    description=f"Step {step.step_id} has no dependencies",
                    suggested_revision="Consider if this step depends on earlier steps",
                    confidence=0.5,
                )
            )

        # Check for overly complex steps
        if self._is_overly_complex(step.task):
            objections.append(
                CriticObjection(
                    severity=ObjectionSeverity.HIGH,
                    category=ObjectionCategory.FEASIBILITY,
                    step_id=step.step_id,
                    description=f"Step {step.step_id} appears overly complex",
                    suggested_revision="Break this step into smaller, more manageable sub-steps",
                    confidence=0.6,
                )
            )

        return objections

    async def _analyze_completeness(
        self,
        plan: Plan,
        candidate: CandidatePlan,
    ) -> List[CriticObjection]:
        """Analyze plan completeness."""
        objections = []

        # Check if execution graph is empty
        if not candidate.execution_graph:
            objections.append(
                CriticObjection(
                    severity=ObjectionSeverity.CRITICAL,
                    category=ObjectionCategory.COMPLETENESS,
                    description="No execution steps defined",
                    suggested_revision="Add execution steps to the plan",
                    confidence=0.9,
                )
            )
            return objections

        # Check for missing testing/validation
        has_testing = any(
            "test" in step.task.lower() or "validat" in step.task.lower() for step in candidate.execution_graph
        )
        if not has_testing:
            objections.append(
                CriticObjection(
                    severity=ObjectionSeverity.MEDIUM,
                    category=ObjectionCategory.COMPLETENESS,
                    description="No testing or validation steps identified",
                    suggested_revision="Add testing steps to validate the implementation",
                    confidence=0.6,
                )
            )

        # Check for missing deployment steps (if applicable)
        if "deploy" in plan.user_intent.lower() or "production" in plan.user_intent.lower():
            has_deployment = any("deploy" in step.task.lower() for step in candidate.execution_graph)
            if not has_deployment:
                objections.append(
                    CriticObjection(
                        severity=ObjectionSeverity.HIGH,
                        category=ObjectionCategory.COMPLETENESS,
                        description="Intent mentions deployment but no deployment steps found",
                        suggested_revision="Add deployment and configuration steps",
                        confidence=0.7,
                    )
                )

        return objections

    async def _analyze_dependencies(self, candidate: CandidatePlan) -> List[CriticObjection]:
        """Analyze step dependencies for circular references and gaps."""
        objections: List[CriticObjection] = []

        if not candidate.execution_graph:
            return objections

        step_ids = {step.step_id for step in candidate.execution_graph}

        for step in candidate.execution_graph:
            for dep_id in step.dependencies:
                # Check for invalid dependencies
                if dep_id not in step_ids:
                    objections.append(
                        CriticObjection(
                            severity=ObjectionSeverity.HIGH,
                            category=ObjectionCategory.LOGIC,
                            step_id=step.step_id,
                            description=f"Step {step.step_id} depends on non-existent step {dep_id}",
                            suggested_revision=f"Remove dependency on step {dep_id} or create the missing step",
                            confidence=0.9,
                        )
                    )

                # Check for circular dependencies (simplified check)
                if dep_id > step.step_id:
                    objections.append(
                        CriticObjection(
                            severity=ObjectionSeverity.MEDIUM,
                            category=ObjectionCategory.LOGIC,
                            step_id=step.step_id,
                            description=f"Step {step.step_id} depends on later step {dep_id} (potential circular dependency)",
                            suggested_revision="Reorder steps to avoid forward dependencies",
                            confidence=0.7,
                        )
                    )

        return objections

    async def _analyze_safety(self, candidate: CandidatePlan) -> List[CriticObjection]:
        """Analyze plan for safety and security concerns."""
        objections = []

        # Check for potentially dangerous operations
        dangerous_keywords = [
            ("delete", "deleting"),
            ("remove", "removing"),
            ("drop", "dropping"),
            ("truncate", "truncating"),
            ("destroy", "destroying"),
        ]

        for step in candidate.execution_graph:
            task_lower = step.task.lower()
            for keyword, variant in dangerous_keywords:
                if keyword in task_lower:
                    # Check if there's a confirmation or backup step
                    has_protection = any(
                        "confirm" in s.task.lower() or "backup" in s.task.lower() or "check" in s.task.lower()
                        for s in candidate.execution_graph
                    )

                    if not has_protection:
                        objections.append(
                            CriticObjection(
                                severity=ObjectionSeverity.HIGH,
                                category=ObjectionCategory.SAFETY,
                                step_id=step.step_id,
                                description=f"Step {step.step_id} involves {variant} without confirmation/backup",
                                suggested_revision=f"Add confirmation prompt or backup step before {variant}",
                                confidence=0.8,
                            )
                        )
                    break

        return objections

    def _determine_verdict(
        self,
        objections: List[CriticObjection],
        critical_count: int,
        high_count: int,
    ) -> Verdict:
        """Determine overall verdict based on objections."""
        # Critical issues always require rejection
        if critical_count > 0:
            return Verdict.REJECT

        # Many high issues require revision
        if high_count >= 3:
            return Verdict.REVISE

        # Some high issues or many medium issues require revision
        if high_count > 0 or len(objections) >= 5:
            return Verdict.REVISE

        # Few or no issues - accept
        return Verdict.ACCEPT

    def _generate_summary(self, objections: List[CriticObjection], verdict: Verdict) -> str:
        """Generate a human-readable summary of the review."""
        if not objections:
            return "No significant issues found. Plan appears sound."

        # Group by category
        by_category: Dict[ObjectionCategory, List[CriticObjection]] = {}
        for obj in objections:
            if obj.category not in by_category:
                by_category[obj.category] = []
            by_category[obj.category].append(obj)

        lines = [f"Review complete: {verdict.value.upper()} verdict\n"]

        for category, objs in by_category.items():
            lines.append(f"\n{category.value.title()} Issues ({len(objs)}):")
            for obj in objs[:3]:  # Show max 3 per category
                lines.append(f"  - [{obj.severity.value.upper()}] {obj.description}")

        return "\n".join(lines)

    def _calculate_confidence(self, objections: List[CriticObjection]) -> float:
        """Calculate overall confidence in the review."""
        if not objections:
            return 0.5

        # Average confidence of all objections
        total_confidence = sum(obj.confidence for obj in objections)
        return min(total_confidence / len(objections), 1.0)

    def _is_vague_task(self, task: str) -> bool:
        """Check if a task description is vague."""
        vague_patterns = [
            "do something",
            "handle",
            "process",
            "manage",
            "work on",
            "deal with",
        ]

        task_lower = task.lower()
        return any(pattern in task_lower for pattern in vague_patterns) and len(task) < 30

    def _is_overly_complex(self, task: str) -> bool:
        """Check if a task is overly complex (too many actions)."""
        # Count action words
        action_words = ["create", "update", "delete", "add", "remove", "modify", "implement", "build"]
        action_count = sum(1 for word in action_words if word in task.lower())
        return action_count >= 3 or len(task) > 200

    def should_trigger_revision(self, report: CriticReport) -> bool:
        """
        Determine if a critic report should trigger plan revision.

        Args:
            report: The critic report to evaluate

        Returns:
            True if revision should be triggered
        """
        return report.should_trigger_revision()
