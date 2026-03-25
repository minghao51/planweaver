"""
PlanWeaver Planner Service

The Planner service handles task decomposition, intent analysis,
and proposal generation. It uses LLMs to break down user intents
into structured execution plans with context awareness.
"""

from typing import Dict, Any, Optional, List
import json
from decimal import Decimal

from ..models.plan import (
    CandidatePlan,
    ContextSuggestion,
    IntentAnalysis,
    OpenQuestion,
    Plan,
    PlanStatus,
    ExecutionStep,
    ExecutionStepsList,
    ExternalContext,
    ProposalAnalysis,
    StrawmanProposal,
    StrawmanProposalInputList,
    StepStatus,
    ProposalWithAnalysis,
)
from .llm_gateway import LLMGateway
from .template_engine import TemplateEngine


class Planner:
    """
    Analyzes user intents and decomposes them into executable plans.

    The Planner is responsible for:
    - Analyzing user intents to identify constraints and missing information
    - Generating clarifying questions to refine requirements
    - Creating strawman proposals with different approaches
    - Decomposing approved approaches into execution DAGs
    - Incorporating external context for context-aware planning

    Attributes:
        llm: LLM gateway for model interactions
        template_engine: Scenario template manager for prompts
    """

    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        template_engine: Optional[TemplateEngine] = None,
    ):
        self.llm = llm_gateway or LLMGateway()
        self.template_engine = template_engine or TemplateEngine()

    def _analyze_proposals_lightweight(self, user_intent: str, proposals: List[dict]) -> Dict[str, dict]:
        """Generate lightweight analysis for proposals without full execution graph."""
        if not proposals:
            return {}

        prompt = f"""You are analyzing planning proposals for complexity and risk.

User Intent: {user_intent}

Proposals to analyze:
{self._format_proposals_for_analysis(proposals)}

For EACH proposal, provide analysis with:
- estimated_step_count: Number of execution steps (integer, typically 3-15)
- complexity_score: "Low", "Medium", or "High" based on technical complexity
- estimated_time_minutes: Total time in minutes (assume ~2 minutes per step average)
- estimated_cost_usd: Cost in USD (assume ~$0.001 per step average)
- risk_factors: List of 2-3 specific risks or challenges
"""
        try:
            response = self.llm.complete(
                model="gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format=ProposalAnalysis,
            )
            parsed = ProposalAnalysis.model_validate_json(response["content"])
            return {k: v.model_dump() for k, v in parsed.proposals.items()}
        except Exception:
            return {
                str(i): {
                    "estimated_step_count": 5,
                    "complexity_score": "Medium",
                    "estimated_time_minutes": 10,
                    "estimated_cost_usd": 0.005,
                    "risk_factors": ["Unknown - analysis failed"],
                }
                for i in range(1, len(proposals) + 1)
            }

    def _format_proposals_for_analysis(self, proposals: List[dict]) -> str:
        """Format proposals for lightweight analysis prompt"""
        formatted = []
        for i, p in enumerate(proposals, 1):
            formatted.append(f"""
Proposal {i}: {p.get("title", "Untitled")}
Approach: {p.get("description", "N/A")}
""")
        return "\n".join(formatted)

    def _build_planner_prompt(self, user_intent: str, plan: Plan) -> str:
        """Build planner prompt with external context"""
        context_brief = plan.metadata.get("context_brief")
        if not plan.external_contexts and not context_brief:
            return f"User Request: {user_intent}"

        lines = [
            "",
            "",
            "=== AVAILABLE CONTEXT ===",
            "",
            "The following external context is available for this planning session. "
            "Use this information to generate better questions and execution steps:",
            "",
        ]
        if isinstance(context_brief, dict):
            synthesized_context = context_brief.get("synthesized_context")
            if synthesized_context:
                lines.extend(
                    [
                        "--- Synthesized Planning Brief ---",
                        synthesized_context,
                        "",
                    ]
                )
        for i, ctx in enumerate(plan.external_contexts, 1):
            lines.extend(
                [
                    f"--- Context Source {i} ({ctx.source_type.upper()}) ---",
                    ctx.content_summary,
                    "",
                ]
            )
        lines.extend(["=== END CONTEXT ===", "", f"User Request: {user_intent}"])
        return "\n".join(lines)

    def _context_references(self, plan: Optional[Plan]) -> List[str]:
        if not plan:
            return []
        references = []
        for context in plan.external_contexts:
            label: str = context.source_type
            if context.metadata.get("filename"):
                label = f"{label}:{context.metadata['filename']}"
            elif context.metadata.get("repo_name"):
                label = f"{label}:{context.metadata['repo_name']}"
            elif context.metadata.get("query"):
                label = f"{label}:{context.metadata['query']}"
            references.append(label)
        return references

    def _proposal_reason(self, plan: Optional[Plan], index: int) -> str:
        if plan and plan.external_contexts:
            return (
                f"Suggested after combining the user intent with {len(plan.external_contexts)}"
                " attached context source(s)."
            )
        return f"Suggested as candidate approach {index} directly from the stated user intent."

    def _analysis_fallback(self) -> Dict[str, Any]:
        return {
            "identified_constraints": [],
            "missing_information": ["Unable to parse analysis"],
            "suggested_approach": "Manual review needed",
            "estimated_complexity": "medium",
        }

    def _parse_execution_steps(self, steps_data: Any, default_model: str) -> List[ExecutionStep]:
        if not isinstance(steps_data, list):
            return self._fallback_execution_steps(default_model)

        steps: List[ExecutionStep] = []
        for step_data in steps_data:
            if not isinstance(step_data, dict):
                continue
            steps.append(
                ExecutionStep(
                    step_id=step_data.get("step_id", 0),
                    task=step_data.get("task", ""),
                    prompt_template_id=step_data.get("prompt_template_id", "default"),
                    assigned_model=step_data.get("assigned_model", default_model),
                    dependencies=step_data.get("dependencies", []),
                    status=StepStatus.PENDING,
                )
            )
        return steps or self._fallback_execution_steps(default_model)

    def _fallback_execution_steps(self, model: str) -> List[ExecutionStep]:
        return [
            ExecutionStep(
                step_id=1,
                task="Execute user request directly",
                prompt_template_id="default",
                assigned_model=model,
                dependencies=[],
            )
        ]

    def _parse_strawman_proposals(self, proposals_data: Any) -> List[StrawmanProposal]:
        if not isinstance(proposals_data, list):
            return []
        try:
            return [StrawmanProposal(**proposal) for proposal in proposals_data if isinstance(proposal, dict)]
        except TypeError:
            return []

    def analyze_intent(
        self,
        user_intent: str,
        plan: Plan,
        scenario_name: Optional[str] = None,
        model: str = "deepseek/deepseek-chat",
    ) -> IntentAnalysis:
        prompt = self._build_planner_prompt(user_intent, plan)

        full_prompt = f"""You are a task decomposition expert. Analyze the following user request and extract key requirements.

{prompt}
"""
        try:
            response = self.llm.complete(
                model=model,
                messages=[{"role": "user", "content": full_prompt}],
                response_format=IntentAnalysis,
            )
            return IntentAnalysis.model_validate_json(response["content"])
        except Exception:
            return IntentAnalysis(**self._analysis_fallback())

    def decompose_into_steps(
        self,
        user_intent: str,
        locked_constraints: Dict[str, Any],
        scenario_name: Optional[str] = None,
        model: str = "deepseek/deepseek-chat",
    ) -> List[ExecutionStep]:
        constraints_str = json.dumps(locked_constraints, indent=2)
        prompt = f"""You are an expert task decomposer. Break down the following request into a dependency graph of steps.

User Request: {user_intent}

Locked Constraints:
{constraints_str}

Return a JSON array of steps. Each step should have:
- step_id: unique integer (starting from 1)
- task: clear description of what this step does
- prompt_template_id: identifier for the prompt template to use
- assigned_model: model to use (claude-3-5-sonnet, gpt-4o, etc.)
- dependencies: array of step_ids that must complete before this step
"""
        try:
            response = self.llm.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=ExecutionStepsList,
            )
            parsed = ExecutionStepsList.model_validate_json(response["content"])
            return parsed.steps
        except Exception:
            return self._fallback_execution_steps(model)

    def generate_strawman_proposals(
        self,
        user_intent: str,
        plan: Optional[Plan] = None,
        model: str = "deepseek/deepseek-chat",
    ) -> List[StrawmanProposal]:
        """Generate strawman proposals with lightweight analysis."""
        prompt_context = self._build_planner_prompt(user_intent, plan or Plan(user_intent=user_intent))
        prompt = f"""You are a strategic advisor. Propose 2-3 different approaches (strawman solutions) for the following request.

{prompt_context}
"""
        try:
            response = self.llm.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=StrawmanProposalInputList,
            )
            parsed = StrawmanProposalInputList.model_validate_json(response["content"])
            raw_proposals = [p.model_dump() for p in parsed.proposals]
        except Exception:
            raw_proposals = []

        proposals_with_analysis = []
        for i, raw_prop in enumerate(raw_proposals, 1):
            prop_id = str(i)

            proposal = StrawmanProposal(
                id=prop_id,
                title=raw_prop.get("title", f"Proposal {i}"),
                description=raw_prop.get("description", ""),
                pros=raw_prop.get("pros", []),
                cons=raw_prop.get("cons", []),
                why_suggested=raw_prop.get("why_suggested") or self._proposal_reason(plan, i),
                context_references=self._context_references(plan),
                confidence=float(raw_prop.get("confidence") or 0.65),
                planning_style=str(raw_prop.get("planning_style", "baseline")),
            )
            proposals_with_analysis.append(proposal)

        return proposals_with_analysis

    def generate_proposals_with_analysis(
        self, user_intent: str, model: str = "deepseek/deepseek-chat"
    ) -> List[ProposalWithAnalysis]:
        """Generate proposals with lightweight analysis for comparison."""
        # First generate the base proposals
        proposals = self.generate_strawman_proposals(user_intent, model=model)

        # Get analysis data again (cached internally by the method)
        raw_proposals = [p.model_dump() for p in proposals]
        analysis = self._analyze_proposals_lightweight(user_intent, raw_proposals)

        # Convert to ProposalWithAnalysis
        proposals_with_analysis = []
        for i, prop in enumerate(proposals, 1):
            analysis_data = analysis.get(
                str(i),
                {
                    "estimated_step_count": 5,
                    "complexity_score": "Medium",
                    "estimated_time_minutes": 10,
                    "estimated_cost_usd": Decimal("0.005"),
                    "risk_factors": [],
                },
            )

            proposals_with_analysis.append(
                ProposalWithAnalysis(
                    proposal_id=prop.id,
                    title=prop.title,
                    description=prop.description,
                    pros=prop.pros,
                    cons=prop.cons,
                    selected=prop.selected,
                    estimated_step_count=analysis_data["estimated_step_count"],
                    complexity_score=analysis_data["complexity_score"],
                    estimated_time_minutes=analysis_data["estimated_time_minutes"],
                    estimated_cost_usd=Decimal(str(analysis_data["estimated_cost_usd"])),
                    risk_factors=analysis_data["risk_factors"],
                )
            )

        return proposals_with_analysis

    def create_initial_plan(
        self,
        user_intent: str,
        scenario_name: Optional[str] = None,
        external_contexts: Optional[List[ExternalContext]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model: str = "deepseek/deepseek-chat",
    ) -> Plan:
        # Create plan first
        plan = Plan(
            user_intent=user_intent,
            scenario_name=scenario_name,
            status=PlanStatus.BRAINSTORMING,
            external_contexts=external_contexts or [],
            metadata=dict(metadata or {}),
        )

        # Analyze with context (plan.external_contexts is empty at this point)
        analysis = self.analyze_intent(user_intent, plan, scenario_name, model)

        for constraint in analysis.identified_constraints:
            plan.lock_constraint(constraint, "extracted from request")

        for question in analysis.missing_information:
            plan.open_questions.append(
                OpenQuestion(
                    question=question,
                    rationale=("The planner needs this detail to reduce ambiguity in the execution graph."),
                    context_references=self._context_references(plan),
                    confidence=0.6,
                )
            )

        return plan

    def refine_plan(
        self,
        plan: Plan,
        user_answers: Dict[str, str],
        model: str = "deepseek/deepseek-chat",
    ) -> Plan:
        for question in plan.open_questions:
            if question.id in user_answers:
                question.answer = user_answers[question.id]
                question.answered = True

        for q_id, answer in user_answers.items():
            plan.lock_constraint(q_id, answer)

        if not plan.open_questions or all(q.answered for q in plan.open_questions):
            plan.status = PlanStatus.AWAITING_APPROVAL
            steps = self.decompose_into_steps(plan.user_intent, plan.locked_constraints, plan.scenario_name, model)
            for step in steps:
                plan.add_step(step)

        return plan

    def suggest_context_sources(
        self,
        user_intent: str,
        external_contexts: Optional[List[Any]] = None,
    ) -> List[ContextSuggestion]:
        existing_types = {context.source_type for context in (external_contexts or [])}
        intent = user_intent.lower()
        suggestions: List[ContextSuggestion] = []

        if (
            any(
                keyword in intent
                for keyword in (
                    "repo",
                    "codebase",
                    "github",
                    "refactor",
                    "frontend",
                    "backend",
                )
            )
            and "github" not in existing_types
        ):
            suggestions.append(
                ContextSuggestion(
                    suggestion_type="github",
                    title="Attach repository context",
                    description="Import a GitHub repository so planning can reference real code structure and dependencies.",
                    reason="The request looks codebase-specific, so repository structure would sharpen the plan.",
                    confidence=0.82,
                )
            )

        if (
            any(
                keyword in intent
                for keyword in (
                    "latest",
                    "best practice",
                    "framework",
                    "migration",
                    "planning",
                    "market",
                    "analysis",
                )
            )
            and "web_search" not in existing_types
        ):
            suggestions.append(
                ContextSuggestion(
                    suggestion_type="web_search",
                    title="Search current best practices",
                    description="Pull in up-to-date guidance before choosing an implementation approach.",
                    reason="The request appears sensitive to current practices or external information.",
                    suggested_query=f"best practices for {user_intent}",
                    confidence=0.76,
                )
            )

        if (
            any(keyword in intent for keyword in ("spec", "document", "brief", "pdf", "requirements"))
            and "file_upload" not in existing_types
        ):
            suggestions.append(
                ContextSuggestion(
                    suggestion_type="file_upload",
                    title="Upload a supporting document",
                    description="Add a requirements doc, spec, or transcript to ground the candidate plans.",
                    reason="A primary document would reduce ambiguity and improve traceability.",
                    confidence=0.71,
                )
            )

        return suggestions

    def regenerate_steps_from_point(
        self,
        user_intent: str,
        locked_constraints: Dict[str, Any],
        candidate: CandidatePlan,
        regenerate_from_step_id: Optional[int],
        note: Optional[str] = None,
        model: str = "deepseek/deepseek-chat",
    ) -> List[ExecutionStep]:
        if regenerate_from_step_id is None:
            raise ValueError("regenerate_from_step requires step_id")

        step_ids = {step.step_id for step in candidate.execution_graph}
        if regenerate_from_step_id not in step_ids:
            raise ValueError(f"Step {regenerate_from_step_id} not found")

        impacted = self._downstream_step_ids(candidate.execution_graph, regenerate_from_step_id)
        preserved = [
            ExecutionStep(**step.model_dump()) for step in candidate.execution_graph if step.step_id not in impacted
        ]
        original = [step.model_dump(mode="json") for step in candidate.execution_graph if step.step_id in impacted]

        prompt = f"""You are refining only part of an execution plan.

User Request: {user_intent}
Locked Constraints:
{json.dumps(locked_constraints, indent=2)}

Candidate Title: {candidate.title}
Planning Style: {candidate.planning_style}

Preserved Steps:
{json.dumps([step.model_dump(mode="json") for step in preserved], indent=2)}

Steps To Replace:
{json.dumps(original, indent=2)}

Additional Guidance:
{note or "Preserve upstream work and regenerate the selected step plus all downstream dependent work."}
"""
        try:
            response = self.llm.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=ExecutionStepsList,
            )
            parsed = ExecutionStepsList.model_validate_json(response["content"])
            replacement_steps = parsed.steps
        except Exception:
            replacement_steps = []

        if not replacement_steps:
            source_step = next(step for step in candidate.execution_graph if step.step_id == regenerate_from_step_id)
            replacement_steps = [
                ExecutionStep(
                    step_id=regenerate_from_step_id,
                    task=f"{source_step.task} (refined)",
                    prompt_template_id=source_step.prompt_template_id,
                    assigned_model=source_step.assigned_model,
                    dependencies=source_step.dependencies,
                )
            ]

        replacement_steps = self._normalize_regenerated_steps(
            preserved,
            replacement_steps,
            regenerate_from_step_id,
        )
        combined = preserved + replacement_steps
        combined.sort(key=lambda step: step.step_id)
        return combined

    def _downstream_step_ids(self, steps: List[ExecutionStep], step_id: int) -> set[int]:
        impacted = {step_id}
        changed = True
        while changed:
            changed = False
            for step in steps:
                if step.step_id in impacted:
                    continue
                if any(dependency in impacted for dependency in step.dependencies):
                    impacted.add(step.step_id)
                    changed = True
        return impacted

    def _normalize_regenerated_steps(
        self,
        preserved_steps: List[ExecutionStep],
        replacement_steps: List[ExecutionStep],
        start_step_id: int,
    ) -> List[ExecutionStep]:
        normalized: List[ExecutionStep] = []
        preserved_ids = {step.step_id for step in preserved_steps}
        generated_ids = [step.step_id for step in replacement_steps]
        id_map = {old_id: start_step_id + offset for offset, old_id in enumerate(generated_ids)}

        for offset, step in enumerate(replacement_steps):
            new_id = start_step_id + offset
            dependencies = []
            for dependency in step.dependencies:
                if dependency in preserved_ids:
                    dependencies.append(dependency)
                elif dependency in id_map:
                    dependencies.append(id_map[dependency])
            if not dependencies and offset == 0:
                source_dependencies = next(
                    (
                        preserved_step.step_id
                        for preserved_step in preserved_steps
                        if preserved_step.step_id < start_step_id
                    ),
                    None,
                )
                if source_dependencies is not None:
                    dependencies = [source_dependencies]

            normalized.append(
                ExecutionStep(
                    step_id=new_id,
                    task=step.task,
                    prompt_template_id=step.prompt_template_id or "default",
                    assigned_model=step.assigned_model,
                    dependencies=dependencies,
                    status=StepStatus.PENDING,
                )
            )
        return normalized
