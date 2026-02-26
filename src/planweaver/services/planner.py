from typing import Dict, Any, Optional, List
import json
from decimal import Decimal

from ..models.plan import (
    Plan,
    PlanStatus,
    ExecutionStep,
    StrawmanProposal,
    StepStatus,
    ProposalWithAnalysis,
)
from .llm_gateway import LLMGateway
from .template_engine import TemplateEngine


class Planner:
    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        template_engine: Optional[TemplateEngine] = None
    ):
        self.llm = llm_gateway or LLMGateway()
        self.template_engine = template_engine or TemplateEngine()

    def _analyze_proposals_lightweight(
        self,
        user_intent: str,
        proposals: List[dict]
    ) -> Dict[str, dict]:
        """Generate lightweight analysis for proposals without full execution graph.

        Uses fast LLM to estimate:
        - Step count
        - Complexity score
        - Estimated time (based on ~2min per step)
        - Estimated cost (based on ~$0.001 per step)
        - Risk factors

        Returns: Dict mapping proposal_id to analysis data
        """
        if not proposals:
            return {}

        prompt = f"""You are analyzing planning proposals for complexity and risk.

User Intent: {user_intent}

Proposals to analyze:
{self._format_proposals_for_analysis(proposals)}

For EACH proposal, provide:
1. estimated_step_count: Number of execution steps (integer, typically 3-15)
2. complexity_score: "Low", "Medium", or "High" based on technical complexity
3. estimated_time_minutes: Total time in minutes (assume ~2 minutes per step average)
4. estimated_cost_usd: Cost in USD (assume ~$0.001 per step average)
5. risk_factors: List of 2-3 specific risks or challenges

Return JSON only, no explanation:
{{
  "1": {{"estimated_step_count": 5, "complexity_score": "Medium", "estimated_time_minutes": 10, "estimated_cost_usd": 0.005, "risk_factors": ["API rate limits", "Data migration"]}},
  "2": {{"estimated_step_count": 3, "complexity_score": "Low", "estimated_time_minutes": 6, "estimated_cost_usd": 0.003, "risk_factors": ["Configuration errors"]}}
}}
"""

        try:
            response = self.llm.complete(
                model="gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                json_mode=True
            )

            # Parse JSON response
            import json
            cleaned = response.get("content", "").strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            analysis_data = json.loads(cleaned)

            # Ensure we got a dict, not a list
            if not isinstance(analysis_data, dict):
                raise ValueError(f"Expected dict, got {type(analysis_data)}")

            return analysis_data

        except Exception as e:
            # Return conservative defaults
            return {
                str(i): {
                    "estimated_step_count": 5,
                    "complexity_score": "Medium",
                    "estimated_time_minutes": 10,
                    "estimated_cost_usd": 0.005,
                    "risk_factors": ["Unknown - analysis failed"]
                }
                for i in range(1, len(proposals) + 1)
            }

    def _format_proposals_for_analysis(self, proposals: List[dict]) -> str:
        """Format proposals for lightweight analysis prompt"""
        formatted = []
        for i, p in enumerate(proposals, 1):
            formatted.append(f"""
Proposal {i}: {p.get('title', 'Untitled')}
Approach: {p.get('description', 'N/A')}
""")
        return "\n".join(formatted)

    def _build_planner_prompt(
        self,
        user_intent: str,
        plan: Plan
    ) -> str:
        """Build planner prompt with external context"""
        if not plan.external_contexts:
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

    def _parse_json_or_default(self, raw_content: str, default: Any) -> Any:
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError:
            return default

    def _analysis_fallback(self) -> Dict[str, Any]:
        return {
            "identified_constraints": [],
            "missing_information": ["Unable to parse analysis"],
            "suggested_approach": "Manual review needed",
            "estimated_complexity": "unknown",
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
        model: str = "deepseek/deepseek-chat"
    ) -> Dict[str, Any]:
        prompt = self._build_planner_prompt(user_intent, plan)

        full_prompt = f"""
You are a task decomposition expert. Analyze the following user request and extract key requirements.

{prompt}

Provide your analysis in JSON format:
{{
    "identified_constraints": [
        "List any constraints mentioned (language, framework, tools, etc.)"
    ],
    "missing_information": [
        "List any questions you have to clarify the request"
    ],
    "suggested_approach": "High-level approach to solve this task",
    "estimated_complexity": "low|medium|high"
}}
"""
        response = self.llm.complete(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            json_mode=True
        )

        return self._parse_json_or_default(response["content"], self._analysis_fallback())

    def decompose_into_steps(
        self,
        user_intent: str,
        locked_constraints: Dict[str, Any],
        scenario_name: Optional[str] = None,
        model: str = "deepseek/deepseek-chat"
    ) -> List[ExecutionStep]:
        constraints_str = json.dumps(locked_constraints, indent=2)
        prompt = f"""
You are an expert task decomposer. Break down the following request into a dependency graph of steps.

User Request: {user_intent}

Locked Constraints:
{constraints_str}

Return a JSON array of steps. Each step should have:
- step_id: unique integer (starting from 1)
- task: clear description of what this step does
- prompt_template_id: identifier for the prompt template to use
- assigned_model: model to use (claude-3-5-sonnet, gpt-4o, etc.)
- dependencies: array of step_ids that must complete before this step

Example output:
[
  {{"step_id": 1, "task": "Create project structure", "prompt_template_id": "create_dirs", "assigned_model": "claude-3-5-sonnet", "dependencies": []}},
  {{"step_id": 2, "task": "Write main application code", "prompt_template_id": "write_main", "assigned_model": "claude-3-5-sonnet", "dependencies": [1]}}
]

Output only valid JSON array, no markdown, no explanation.
"""
        response = self.llm.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            json_mode=True
        )

        steps_data = self._parse_json_or_default(response["content"], [])
        return self._parse_execution_steps(steps_data, model)

    def generate_strawman_proposals(
        self,
        user_intent: str,
        model: str = "deepseek/deepseek-chat"
    ) -> List[StrawmanProposal]:
        """Generate strawman proposals with lightweight analysis."""
        prompt = f"""
You are a strategic advisor. Propose 2-3 different approaches (strawman solutions) for the following request.

User Request: {user_intent}

For each approach, provide:
- title: Short name for the approach
- description: What this approach does
- pros: Why this approach is good (2-3 points)
- cons: Why this approach might not be ideal (2-3 points)

Return JSON array:
[
  {{"title": "Approach 1", "description": "...", "pros": [...], "cons": [...]}}
]
"""
        response = self.llm.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            json_mode=True
        )

        proposals_data = self._parse_json_or_default(response["content"], [])
        raw_proposals = proposals_data if isinstance(proposals_data, list) else []

        # Generate lightweight analysis
        analysis = self._analyze_proposals_lightweight(user_intent, raw_proposals)

        # Merge proposals with analysis
        proposals_with_analysis = []
        for i, raw_prop in enumerate(raw_proposals, 1):
            prop_id = str(i)  # Use string index as ID
            analysis_data = analysis.get(str(i), {
                "estimated_step_count": 5,
                "complexity_score": "Medium",
                "estimated_time_minutes": 10,
                "estimated_cost_usd": Decimal("0.005"),
                "risk_factors": []
            })

            # Create StrawmanProposal (for backwards compatibility)
            proposal = StrawmanProposal(
                id=prop_id,
                title=raw_prop.get("title", f"Proposal {i}"),
                description=raw_prop.get("description", ""),
                pros=raw_prop.get("pros", []),
                cons=raw_prop.get("cons", [])
            )
            proposals_with_analysis.append(proposal)

        return proposals_with_analysis

    def generate_proposals_with_analysis(
        self,
        user_intent: str,
        model: str = "deepseek/deepseek-chat"
    ) -> List[ProposalWithAnalysis]:
        """Generate proposals with lightweight analysis for comparison."""
        # First generate the base proposals
        proposals = self.generate_strawman_proposals(user_intent, model)

        # Get analysis data again (cached internally by the method)
        raw_proposals = [p.model_dump() for p in proposals]
        analysis = self._analyze_proposals_lightweight(user_intent, raw_proposals)

        # Convert to ProposalWithAnalysis
        proposals_with_analysis = []
        for i, prop in enumerate(proposals, 1):
            analysis_data = analysis.get(str(i), {
                "estimated_step_count": 5,
                "complexity_score": "Medium",
                "estimated_time_minutes": 10,
                "estimated_cost_usd": Decimal("0.005"),
                "risk_factors": []
            })

            proposals_with_analysis.append(ProposalWithAnalysis(
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
                risk_factors=analysis_data["risk_factors"]
            ))

        return proposals_with_analysis

    def create_initial_plan(
        self,
        user_intent: str,
        scenario_name: Optional[str] = None,
        model: str = "deepseek/deepseek-chat"
    ) -> Plan:
        # Create plan first
        plan = Plan(
            user_intent=user_intent,
            scenario_name=scenario_name,
            status=PlanStatus.BRAINSTORMING
        )

        # Analyze with context (plan.external_contexts is empty at this point)
        analysis = self.analyze_intent(user_intent, plan, scenario_name, model)

        for constraint in analysis.get("identified_constraints", []):
            plan.lock_constraint(constraint, "extracted from request")

        for question in analysis.get("missing_information", []):
            plan.add_open_question(question)

        return plan

    def refine_plan(
        self,
        plan: Plan,
        user_answers: Dict[str, str],
        model: str = "deepseek/deepseek-chat"
    ) -> Plan:
        for question in plan.open_questions:
            if question.id in user_answers:
                question.answer = user_answers[question.id]
                question.answered = True

        for q_id, answer in user_answers.items():
            plan.lock_constraint(q_id, answer)

        if not plan.open_questions or all(q.answered for q in plan.open_questions):
            plan.status = PlanStatus.AWAITING_APPROVAL
            steps = self.decompose_into_steps(
                plan.user_intent,
                plan.locked_constraints,
                plan.scenario_name,
                model
            )
            for step in steps:
                plan.add_step(step)

        return plan
