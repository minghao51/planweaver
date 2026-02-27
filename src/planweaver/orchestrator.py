from typing import Dict, Any, Optional, List

from .models.plan import Plan, PlanStatus, ExecutionStep, ExternalContext
from .services.planner import Planner
from .services.router import ExecutionRouter
from .services.template_engine import TemplateEngine
from .services.llm_gateway import LLMGateway
from .db.repositories import PlanRepository


class Orchestrator:
    def __init__(
        self,
        planner_model: str = "gemini-2.5-flash",
        executor_model: str = "gemini-3-flash",
        scenarios_path: str = "scenarios"
    ):
        self.planner_model = planner_model
        self.executor_model = executor_model
        self.template_engine = TemplateEngine(scenarios_path)
        self.llm = LLMGateway()
        self.planner = Planner(self.llm, self.template_engine)
        self.router = ExecutionRouter(self.llm, self.template_engine)
        self.plan_repository = PlanRepository()

    def start_session(
        self,
        user_intent: str,
        scenario_name: Optional[str] = None,
        external_contexts: Optional[List[ExternalContext]] = None,
        planner_model: Optional[str] = None,
        executor_model: Optional[str] = None
    ) -> Plan:
        # Use provided models or fall back to instance defaults
        planner = planner_model or self.planner_model
        executor = executor_model or self.executor_model

        plan = self.planner.create_initial_plan(
            user_intent=user_intent,
            scenario_name=scenario_name,
            model=planner
        )
        # Store executor model for later use
        plan.executor_model = executor
        plan.external_contexts = external_contexts or []
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

    def add_external_context(
        self,
        session_id: str,
        context: ExternalContext
    ) -> Plan:
        """Add external context to a planning session"""
        plan = self.plan_repository.get(session_id)
        if not plan:
            raise ValueError(f"Session {session_id} not found")

        # Add context to plan
        plan.external_contexts.append(context)

        # Save to database
        self.plan_repository.save(plan)

        return plan

    def get_strawman_proposals(self, plan: Plan) -> List[Dict[str, Any]]:
        proposals = self.planner.generate_strawman_proposals(
            plan.user_intent,
            model=self.planner_model
        )
        plan.strawman_proposals = proposals
        self.plan_repository.save(plan)
        return [p.model_dump() for p in proposals]

    def select_proposal(self, plan: Plan, proposal_id: str) -> Plan:
        for proposal in plan.strawman_proposals:
            if proposal.id == proposal_id:
                proposal.selected = True
                plan.lock_constraint("selected_approach", proposal.title)
                plan.lock_constraint("approach_description", proposal.description)
                break
        self.plan_repository.save(plan)
        return plan

    def answer_questions(
        self,
        plan: Plan,
        answers: Dict[str, str]
    ) -> Plan:
        plan = self.planner.refine_plan(
            plan=plan,
            user_answers=answers,
            model=self.planner_model
        )
        self.plan_repository.save(plan)
        return plan

    def approve_plan(self, plan: Plan) -> Plan:
        plan.status = PlanStatus.APPROVED
        self.plan_repository.save(plan)
        return plan

    async def execute(self, plan: Plan, context: Optional[Dict[str, Any]] = None) -> Plan:
        if plan.status != PlanStatus.APPROVED:
            raise ValueError("Plan must be APPROVED before execution")

        plan = await self.router.execute_plan(
            plan=plan,
            context=context or {}
        )

        self.plan_repository.save(plan)
        return plan

    def get_next_executable_step(self, plan: Plan) -> Optional[ExecutionStep]:
        return self.router.get_executable_steps(plan)[0] if plan.execution_graph else None
