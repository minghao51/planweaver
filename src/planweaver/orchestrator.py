"""
PlanWeaver Orchestrator Module

The Orchestrator is the main coordinator for planning sessions.
It manages the lifecycle of plans from creation through execution,
including handling external contexts, coordinating between the
planner and execution router, and persisting state to the database.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Iterable
from datetime import datetime, timezone

from .models.plan import (
    CandidatePlan,
    CandidatePlanRevision,
    CandidatePlanStatus,
    ContextSuggestion,
    ExecutionStep,
    ExternalContext,
    ManualPlanSubmission,
    Plan,
    PlanSourceType,
    PlanStatus,
    PlanningOutcome,
)
from .services.plan_normalizer import PlanNormalizer
from .services.planner import Planner
from .services.router import ExecutionRouter
from .services.template_engine import TemplateEngine
from .services.llm_gateway import LLMGateway
from .db.repositories import PlanRepository
from .scout import PreconditionScout


PLANNING_STYLES = ("baseline", "fast", "risk_averse", "cost_aware")


class Orchestrator:
    """
    Main coordinator for PlanWeaver planning sessions.
    """

    def __init__(
        self,
        planner_model: str = "gemini-2.5-flash",
        executor_model: str = "gemini-3-flash",
        scenarios_path: str = "scenarios",
        scout_enabled: bool = False,
    ):
        self.planner_model = planner_model
        self.executor_model = executor_model
        self.template_engine = TemplateEngine(scenarios_path)
        self.llm = LLMGateway()
        self.planner = Planner(self.llm, self.template_engine)
        self.router = ExecutionRouter(self.llm, self.template_engine)
        self.plan_repository = PlanRepository()
        self.plan_normalizer = PlanNormalizer()
        self.scout = PreconditionScout()
        self.scout_enabled = scout_enabled

    def start_session(
        self,
        user_intent: str,
        scenario_name: Optional[str] = None,
        external_contexts: Optional[List[ExternalContext]] = None,
        planner_model: Optional[str] = None,
        executor_model: Optional[str] = None,
    ) -> Plan:
        planner = planner_model or self.planner_model

        plan = self.planner.create_initial_plan(user_intent=user_intent, scenario_name=scenario_name, model=planner)
        plan.planner_model = planner_model
        plan.executor_model = executor_model
        plan.external_contexts = external_contexts or []
        plan.context_suggestions = self._safe_suggestions(
            self.planner.suggest_context_sources(user_intent, plan.external_contexts)
        )
        self._ensure_seed_candidate(plan)
        if plan.external_contexts:
            self._refresh_candidate_context_references(plan)
        self.plan_repository.save(plan)
        return plan

    def get_session(self, session_id: str) -> Optional[Plan]:
        return self.plan_repository.get(session_id)

    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.plan_repository.list_summaries(
            limit=limit,
            offset=offset,
            status=status,
            query=query,
        )

    def add_external_context(self, session_id: str, context: ExternalContext) -> Plan:
        plan = self.plan_repository.get(session_id)
        if not plan:
            raise ValueError(f"Session {session_id} not found")

        plan.external_contexts.append(context)
        plan.context_suggestions = self._safe_suggestions(
            self.planner.suggest_context_sources(plan.user_intent, plan.external_contexts)
        )
        self._refresh_candidate_context_references(plan)
        self.plan_repository.save(plan)
        return plan

    def get_strawman_proposals(self, plan: Plan) -> List[Dict[str, Any]]:
        proposals = self.planner.generate_strawman_proposals(
            plan.user_intent,
            plan=plan if plan.external_contexts else None,
            model=plan.planner_model or self.planner_model,
        )
        plan.strawman_proposals = proposals
        self.plan_repository.save(plan)
        return [p.model_dump() for p in proposals]

    def list_candidates(self, plan: Plan) -> List[CandidatePlan]:
        if not plan.candidate_plans:
            self._ensure_seed_candidate(plan)
            self.plan_repository.save(plan)
        return plan.candidate_plans

    def select_proposal(self, plan: Plan, proposal_id: str) -> Plan:
        selected_proposal = None
        for proposal in plan.strawman_proposals:
            proposal.selected = proposal.id == proposal_id
            if proposal.selected:
                selected_proposal = proposal

        if not selected_proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        plan.lock_constraint("selected_approach", selected_proposal.title)
        plan.lock_constraint("approach_description", selected_proposal.description)
        created_candidates = self._ensure_proposal_candidates(plan, selected_proposal.id)
        if created_candidates:
            baseline_candidate = next(
                (candidate for candidate in created_candidates if candidate.planning_style == "baseline"),
                created_candidates[0],
            )
            plan.selected_candidate_id = baseline_candidate.candidate_id
            for candidate in plan.candidate_plans:
                if candidate.candidate_id == baseline_candidate.candidate_id:
                    candidate.status = CandidatePlanStatus.SELECTED
                elif candidate.status == CandidatePlanStatus.SELECTED:
                    candidate.status = CandidatePlanStatus.DRAFT

            self._record_outcome(
                plan,
                event_type="proposal_selected",
                candidate_id=baseline_candidate.candidate_id,
                summary=f"Selected proposal '{selected_proposal.title}'.",
                metadata={"proposal_id": selected_proposal.id},
            )

        self.plan_repository.save(plan)
        return plan

    def answer_questions(self, plan: Plan, answers: Dict[str, str]) -> Plan:
        plan = self.planner.refine_plan(
            plan=plan,
            user_answers=answers,
            model=plan.planner_model or self.planner_model,
        )
        plan.context_suggestions = self._safe_suggestions(
            self.planner.suggest_context_sources(plan.user_intent, plan.external_contexts)
        )
        self._ensure_seed_candidate(plan)
        self.plan_repository.save(plan)
        return plan

    def approve_plan(self, plan: Plan) -> Plan:
        if not plan.execution_graph:
            raise ValueError("No candidate execution graph has been adopted yet.")
        plan.status = PlanStatus.APPROVED
        self._record_outcome(
            plan,
            event_type="plan_approved",
            candidate_id=plan.approved_candidate_id,
            summary="The session plan was approved for execution.",
        )
        self.plan_repository.save(plan)
        return plan

    def approve_candidate(self, plan: Plan, candidate_id: str) -> Plan:
        candidate = plan.get_candidate_by_id(candidate_id)
        plan.selected_candidate_id = candidate.candidate_id
        plan.approved_candidate_id = candidate.candidate_id
        plan.execution_graph = [ExecutionStep(**step.model_dump()) for step in candidate.execution_graph]
        if plan.status == PlanStatus.BRAINSTORMING:
            plan.status = PlanStatus.AWAITING_APPROVAL

        for other in plan.candidate_plans:
            if other.candidate_id == candidate_id:
                other.status = CandidatePlanStatus.APPROVED
            elif other.status == CandidatePlanStatus.APPROVED:
                other.status = CandidatePlanStatus.SUPERSEDED
            elif other.candidate_id == plan.selected_candidate_id:
                other.status = CandidatePlanStatus.SELECTED

        self._record_revision(plan, candidate, "approved", "Candidate adopted into the session plan.")
        self._record_outcome(
            plan,
            event_type="candidate_approved",
            candidate_id=candidate.candidate_id,
            summary=f"Approved candidate '{candidate.title}'.",
            metadata={"planning_style": candidate.planning_style},
        )
        self.plan_repository.save(plan)
        return plan

    async def scout_plan(self, plan: Plan) -> Plan:
        """
        Run precondition scouting on the plan's execution graph.

        Identifies and validates preconditions before execution.
        Annotates steps with validation results.
        """
        if not self.scout_enabled:
            return plan

        report = await self.scout.scout_plan(plan)
        if report.has_failed_preconditions():
            plan.metadata["scout_failed_preconditions"] = [
                {
                    "step_id": p.step_id,
                    "type": p.precondition_type,
                    "check": p.check_expression,
                    "error": p.probe_error,
                }
                for p in report.failed
            ]
        plan.metadata["scout_report"] = {
            "total": len(report.preconditions),
            "failed": len(report.failed),
            "unverifiable": len(report.unverifiable),
        }
        plan = self.scout.annotate_plan(plan, report)
        self.plan_repository.save(plan)
        return plan

    def branch_candidate(
        self,
        plan: Plan,
        candidate_id: str,
        title: Optional[str] = None,
        note: Optional[str] = None,
    ) -> CandidatePlan:
        source = plan.get_candidate_by_id(candidate_id)
        clone = CandidatePlan(
            session_id=plan.session_id,
            title=title or f"{source.title} branch",
            summary=source.summary,
            source_type=source.source_type,
            source_model=source.source_model,
            planning_style=source.planning_style,
            parent_candidate_id=source.candidate_id,
            proposal_id=source.proposal_id,
            status=CandidatePlanStatus.DRAFT,
            execution_graph=[ExecutionStep(**step.model_dump()) for step in source.execution_graph],
            context_references=list(source.context_references),
            confidence=source.confidence,
            why_suggested=source.why_suggested,
            metadata=dict(source.metadata),
        )
        self._refresh_candidate_normalization(clone, plan)
        plan.upsert_candidate(clone)
        self._record_revision(plan, clone, "branched", note or "Candidate branched from an existing plan.")
        self._record_outcome(
            plan,
            event_type="candidate_branched",
            candidate_id=clone.candidate_id,
            summary=f"Created candidate branch '{clone.title}'.",
            metadata={"parent_candidate_id": source.candidate_id},
        )
        self.plan_repository.save(plan)
        return clone

    def refine_candidate(
        self,
        plan: Plan,
        candidate_id: str,
        operation: str,
        *,
        step_id: Optional[int] = None,
        task: Optional[str] = None,
        insert_after_step_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> CandidatePlan:
        candidate = plan.get_candidate_by_id(candidate_id)

        if operation == "edit_step":
            self._edit_candidate_step(candidate, step_id, task)
        elif operation == "delete_step":
            self._delete_candidate_step(candidate, step_id)
        elif operation == "add_step":
            self._add_candidate_step(candidate, task, insert_after_step_id)
        elif operation == "regenerate_from_step":
            candidate.execution_graph = self.planner.regenerate_steps_from_point(
                user_intent=plan.user_intent,
                locked_constraints=plan.locked_constraints,
                candidate=candidate,
                regenerate_from_step_id=step_id,
                note=note,
                model=plan.planner_model or self.planner_model,
            )
        else:
            raise ValueError(f"Unsupported refine operation '{operation}'")

        self._refresh_candidate_normalization(candidate, plan)
        plan.upsert_candidate(candidate)
        if plan.approved_candidate_id == candidate.candidate_id:
            plan.execution_graph = [ExecutionStep(**step.model_dump()) for step in candidate.execution_graph]
        self._record_revision(
            plan,
            candidate,
            operation,
            note or f"Applied {operation} to candidate '{candidate.title}'.",
        )
        self._record_outcome(
            plan,
            event_type="candidate_refined",
            candidate_id=candidate.candidate_id,
            summary=f"Updated candidate '{candidate.title}' via {operation}.",
            metadata={"operation": operation, "step_id": step_id},
        )
        self.plan_repository.save(plan)
        return candidate

    async def execute(self, plan: Plan, context: Optional[Dict[str, Any]] = None) -> Plan:
        if plan.status != PlanStatus.APPROVED:
            raise ValueError("Plan must be APPROVED before execution")

        plan = await self.router.execute_plan(plan=plan, context=context or {}, model_override=plan.executor_model)

        self._record_outcome(
            plan,
            event_type=("execution_completed" if plan.status == PlanStatus.COMPLETED else "execution_failed"),
            candidate_id=plan.approved_candidate_id,
            summary=(
                "Execution completed successfully."
                if plan.status == PlanStatus.COMPLETED
                else "Execution failed before all steps completed."
            ),
            metadata={"final_status": plan.status.value},
        )
        self.plan_repository.save(plan)
        return plan

    def get_next_executable_step(self, plan: Plan) -> Optional[ExecutionStep]:
        return self.router.get_executable_steps(plan)[0] if plan.execution_graph else None

    def register_manual_candidate(self, session_id: str, submission: ManualPlanSubmission) -> CandidatePlan:
        plan = self.plan_repository.get(session_id)
        if not plan:
            raise ValueError(f"Session {session_id} not found")

        normalized = self.plan_normalizer.normalize_manual_plan(submission)
        candidate = CandidatePlan(
            session_id=session_id,
            title=normalized.title,
            summary=normalized.summary,
            source_type=PlanSourceType.MANUAL,
            source_model="human",
            planning_style="manual",
            status=CandidatePlanStatus.SELECTED,
            normalized_plan_id=normalized.id,
            normalized_plan=normalized.model_dump(mode="json"),
            execution_graph=self._steps_from_normalized_plan(normalized.steps),
            context_references=self._context_reference_labels(plan.external_contexts),
            confidence=0.7,
            why_suggested="Added manually by the user as a baseline candidate.",
            metadata={"origin": "manual"},
        )
        for existing in plan.candidate_plans:
            if existing.status == CandidatePlanStatus.SELECTED:
                existing.status = CandidatePlanStatus.DRAFT
        plan.upsert_candidate(candidate)
        plan.selected_candidate_id = candidate.candidate_id
        self._record_revision(plan, candidate, "manual", "Manual candidate added.")
        self._record_outcome(
            plan,
            event_type="manual_candidate_added",
            candidate_id=candidate.candidate_id,
            summary=f"Added manual candidate '{candidate.title}'.",
        )
        self.plan_repository.save(plan)
        return candidate

    def get_outcomes(self, plan: Plan) -> List[PlanningOutcome]:
        return plan.planning_outcomes

    def _ensure_seed_candidate(self, plan: Plan) -> CandidatePlan:
        if plan.candidate_plans:
            return plan.candidate_plans[0]

        steps: List[ExecutionStep] = []
        if not plan.open_questions:
            steps = self.planner.decompose_into_steps(
                user_intent=plan.user_intent,
                locked_constraints=plan.locked_constraints,
                scenario_name=plan.scenario_name,
                model=plan.planner_model or self.planner_model,
            )
            if not isinstance(steps, list):
                steps = []

        candidate = CandidatePlan(
            session_id=plan.session_id,
            title="Initial baseline",
            summary=plan.user_intent,
            source_type=PlanSourceType.LLM_GENERATED,
            source_model=plan.planner_model or self.planner_model,
            planning_style="baseline",
            execution_graph=steps,
            context_references=self._context_reference_labels(plan.external_contexts),
            confidence=0.55,
            why_suggested="Seeded from the initial user intent to establish a baseline candidate.",
            metadata={"origin": "seed"},
        )
        self._refresh_candidate_normalization(candidate, plan)
        plan.upsert_candidate(candidate)
        plan.selected_candidate_id = candidate.candidate_id
        self._record_revision(plan, candidate, "created", "Seed baseline candidate created.")
        return candidate

    def _ensure_proposal_candidates(self, plan: Plan, proposal_id: str) -> List[CandidatePlan]:
        existing = [
            candidate
            for candidate in plan.candidate_plans
            if candidate.proposal_id == proposal_id and candidate.metadata.get("origin") == "proposal"
        ]
        if existing:
            return existing

        proposal = plan.get_proposal_by_id(proposal_id)
        created: List[CandidatePlan] = []
        for style in PLANNING_STYLES:
            constraints = {
                **plan.locked_constraints,
                "selected_approach": proposal.title,
                "approach_description": proposal.description,
                "planning_style": style,
            }
            steps = self.planner.decompose_into_steps(
                user_intent=plan.user_intent,
                locked_constraints=constraints,
                scenario_name=plan.scenario_name,
                model=plan.planner_model or self.planner_model,
            )
            candidate = CandidatePlan(
                session_id=plan.session_id,
                title=f"{proposal.title} ({style.replace('_', ' ')})",
                summary=proposal.description,
                source_type=PlanSourceType.LLM_GENERATED,
                source_model=plan.planner_model or self.planner_model,
                planning_style=style,
                proposal_id=proposal.id,
                status=CandidatePlanStatus.SELECTED if style == "baseline" else CandidatePlanStatus.DRAFT,
                execution_graph=steps,
                context_references=list(proposal.context_references),
                confidence=proposal.confidence or 0.65,
                why_suggested=proposal.why_suggested,
                metadata={"origin": "proposal", "proposal_id": proposal.id},
            )
            self._refresh_candidate_normalization(candidate, plan)
            plan.upsert_candidate(candidate)
            self._record_revision(
                plan,
                candidate,
                "created",
                f"Generated {style} candidate from proposal '{proposal.title}'.",
            )
            created.append(candidate)
        return created

    def _refresh_candidate_normalization(self, candidate: CandidatePlan, plan: Plan) -> None:
        normalized = self.plan_normalizer.normalize_generated_plan(
            {
                "id": candidate.candidate_id,
                "title": candidate.title,
                "summary": candidate.summary,
                "execution_graph": [step.model_dump(mode="json") for step in candidate.execution_graph],
                "success_criteria": candidate.metadata.get("success_criteria", []),
                "risks": candidate.metadata.get("risks", []),
                "fallbacks": candidate.metadata.get("fallbacks", []),
                "metadata": {
                    **candidate.metadata,
                    "context_references": candidate.context_references,
                },
            },
            session_id=plan.session_id,
            source_type=candidate.source_type,
            source_model=candidate.source_model,
            planning_style=candidate.planning_style,
        )
        candidate.normalized_plan_id = normalized.id
        candidate.normalized_plan = normalized.model_dump(mode="json")
        candidate.updated_at = datetime.now(timezone.utc)

    def _record_revision(
        self,
        plan: Plan,
        candidate: CandidatePlan,
        revision_type: str,
        note: Optional[str],
    ) -> None:
        plan.record_candidate_revision(
            CandidatePlanRevision(
                candidate_id=candidate.candidate_id,
                session_id=plan.session_id,
                revision_type=revision_type,
                title=candidate.title,
                summary=candidate.summary,
                execution_graph=[ExecutionStep(**step.model_dump()) for step in candidate.execution_graph],
                note=note,
                metadata={"status": candidate.status.value},
            )
        )

    def _record_outcome(
        self,
        plan: Plan,
        *,
        event_type: str,
        summary: str,
        candidate_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        plan.record_outcome(
            PlanningOutcome(
                session_id=plan.session_id,
                candidate_id=candidate_id,
                event_type=event_type,
                summary=summary,
                metadata=metadata or {},
            )
        )

    def _refresh_candidate_context_references(self, plan: Plan) -> None:
        references = self._context_reference_labels(plan.external_contexts)
        for candidate in plan.candidate_plans:
            candidate.context_references = references
            self._refresh_candidate_normalization(candidate, plan)

    def _safe_suggestions(self, suggestions: Any) -> List[ContextSuggestion]:
        return suggestions if isinstance(suggestions, list) else []

    def _context_reference_labels(self, contexts: Iterable[ExternalContext]) -> List[str]:
        labels: List[str] = []
        for context in contexts:
            label: str = context.source_type
            if context.metadata.get("filename"):
                label = f"{label}:{context.metadata['filename']}"
            elif context.metadata.get("repo_name"):
                label = f"{label}:{context.metadata['repo_name']}"
            elif context.metadata.get("query"):
                label = f"{label}:{context.metadata['query']}"
            labels.append(label)
        return labels

    def _steps_from_normalized_plan(self, steps) -> List[ExecutionStep]:
        execution_steps: List[ExecutionStep] = []
        id_map: Dict[str, int] = {}
        for index, step in enumerate(steps, start=1):
            id_map[step.step_id] = index
            execution_steps.append(
                ExecutionStep(
                    step_id=index,
                    task=step.description,
                    prompt_template_id="default",
                    assigned_model=step.owner_model or self.executor_model,
                    dependencies=[],
                )
            )
        for execution_step, normalized_step in zip(execution_steps, steps):
            execution_step.dependencies = [
                id_map[dependency] for dependency in normalized_step.dependencies if dependency in id_map
            ]
        return execution_steps

    def _edit_candidate_step(self, candidate: CandidatePlan, step_id: Optional[int], task: Optional[str]) -> None:
        if step_id is None or not task:
            raise ValueError("edit_step requires step_id and task")
        for step in candidate.execution_graph:
            if step.step_id == step_id:
                step.task = task
                return
        raise ValueError(f"Step {step_id} not found")

    def _delete_candidate_step(self, candidate: CandidatePlan, step_id: Optional[int]) -> None:
        if step_id is None:
            raise ValueError("delete_step requires step_id")
        remaining = [step for step in candidate.execution_graph if step.step_id != step_id]
        if len(remaining) == len(candidate.execution_graph):
            raise ValueError(f"Step {step_id} not found")
        for step in remaining:
            step.dependencies = [dependency for dependency in step.dependencies if dependency != step_id]
        candidate.execution_graph = remaining

    def _add_candidate_step(
        self,
        candidate: CandidatePlan,
        task: Optional[str],
        insert_after_step_id: Optional[int],
    ) -> None:
        if not task:
            raise ValueError("add_step requires task")
        next_step_id = max((step.step_id for step in candidate.execution_graph), default=0) + 1
        dependencies = [insert_after_step_id] if insert_after_step_id else []
        candidate.execution_graph.append(
            ExecutionStep(
                step_id=next_step_id,
                task=task,
                prompt_template_id="default",
                assigned_model=self.executor_model,
                dependencies=[dep for dep in dependencies if dep is not None],
            )
        )
