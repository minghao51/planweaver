from typing import Dict, Any, Optional, List
import json

from ..models.plan import Plan, PlanStatus, ExecutionStep, StrawmanProposal, StepStatus
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

    def analyze_intent(
        self,
        user_intent: str,
        scenario_name: Optional[str] = None,
        model: str = "deepseek/deepseek-chat"
    ) -> Dict[str, Any]:
        prompt = f"""
You are a task decomposition expert. Analyze the following user request and extract key requirements.

User Request: {user_intent}

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
            messages=[{"role": "user", "content": prompt}],
            json_mode=True
        )

        try:
            return json.loads(response["content"])
        except json.JSONDecodeError:
            return {
                "identified_constraints": [],
                "missing_information": ["Unable to parse analysis"],
                "suggested_approach": "Manual review needed",
                "estimated_complexity": "unknown"
            }

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

        try:
            steps_data = json.loads(response["content"])
            steps = []
            for step_data in steps_data:
                steps.append(ExecutionStep(
                    step_id=step_data.get("step_id", 0),
                    task=step_data.get("task", ""),
                    prompt_template_id=step_data.get("prompt_template_id", "default"),
                    assigned_model=step_data.get("assigned_model", model),
                    dependencies=step_data.get("dependencies", []),
                    status=StepStatus.PENDING
                ))
            return steps
        except json.JSONDecodeError:
            return [ExecutionStep(
                step_id=1,
                task="Execute user request directly",
                prompt_template_id="default",
                assigned_model=model,
                dependencies=[]
            )]

    def generate_strawman_proposals(
        self,
        user_intent: str,
        model: str = "deepseek/deepseek-chat"
    ) -> List[StrawmanProposal]:
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
  {{"title": "Approach 1", "description": "...", "pros": [...], "cons": [...]}},
  {{"title": "Approach 2", "description": "...", "pros": [...], "cons": [...]}}
]
"""
        response = self.llm.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            json_mode=True
        )

        try:
            proposals_data = json.loads(response["content"])
            return [
                StrawmanProposal(**p) for p in proposals_data
            ]
        except (json.JSONDecodeError, TypeError):
            return []

    def create_initial_plan(
        self,
        user_intent: str,
        scenario_name: Optional[str] = None,
        model: str = "deepseek/deepseek-chat"
    ) -> Plan:
        analysis = self.analyze_intent(user_intent, scenario_name, model)

        plan = Plan(
            user_intent=user_intent,
            scenario_name=scenario_name,
            status=PlanStatus.BRAINSTORMING
        )

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
