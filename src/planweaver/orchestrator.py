from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .models.plan import Plan, PlanStatus, ExecutionStep
from .services.planner import Planner
from .services.router import ExecutionRouter
from .services.template_engine import TemplateEngine
from .services.llm_gateway import LLMGateway
from .db.database import get_session
from .db.models import SessionModel as DBSession


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

    def start_session(
        self,
        user_intent: str,
        scenario_name: Optional[str] = None
    ) -> Plan:
        plan = self.planner.create_initial_plan(
            user_intent=user_intent,
            scenario_name=scenario_name,
            model=self.planner_model
        )
        self._save_plan(plan)
        return plan

    def get_session(self, session_id: str) -> Optional[Plan]:
        db_session = get_session()
        try:
            db_plan = db_session.query(DBSession).filter_by(id=session_id).first()
            if not db_plan:
                return None
            return self._db_to_plan(db_plan)
        finally:
            db_session.close()

    def get_strawman_proposals(self, plan: Plan) -> List[Dict[str, Any]]:
        proposals = self.planner.generate_strawman_proposals(
            plan.user_intent,
            model=self.planner_model
        )
        plan.strawman_proposals = proposals
        self._save_plan(plan)
        return [p.model_dump() for p in proposals]

    def select_proposal(self, plan: Plan, proposal_id: str) -> Plan:
        for proposal in plan.strawman_proposals:
            if proposal.id == proposal_id:
                proposal.selected = True
                plan.lock_constraint("selected_approach", proposal.title)
                plan.lock_constraint("approach_description", proposal.description)
                break
        self._save_plan(plan)
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
        self._save_plan(plan)
        return plan

    def approve_plan(self, plan: Plan) -> Plan:
        plan.status = PlanStatus.APPROVED
        self._save_plan(plan)
        return plan

    def execute(self, plan: Plan, context: Optional[Dict[str, Any]] = None) -> Plan:
        if plan.status != PlanStatus.APPROVED:
            raise ValueError("Plan must be APPROVED before execution")

        plan = self.router.execute_plan(
            plan=plan,
            context=context or {}
        )

        self._save_plan(plan)
        return plan

    def get_next_executable_step(self, plan: Plan) -> Optional[ExecutionStep]:
        return self.router.get_executable_steps(plan)[0] if plan.execution_graph else None

    def _save_plan(self, plan: Plan) -> None:
        db_session = get_session()
        try:
            existing = db_session.query(DBSession).filter_by(id=plan.session_id).first()

            if existing:
                existing.user_intent = plan.user_intent
                existing.scenario_name = plan.scenario_name
                existing.status = plan.status.value
                existing.locked_constraints = plan.locked_constraints
                existing.open_questions = [q.model_dump() for q in plan.open_questions]
                existing.strawman_proposals = [p.model_dump() for p in plan.strawman_proposals]
                existing.execution_graph = [s.model_dump() for s in plan.execution_graph]
                existing.final_output = plan.final_output
                existing.updated_at = datetime.now(timezone.utc)
            else:
                db_plan = DBSession(
                    id=plan.session_id,
                    user_intent=plan.user_intent,
                    scenario_name=plan.scenario_name,
                    status=plan.status.value,
                    locked_constraints=plan.locked_constraints,
                    open_questions=[q.model_dump() for q in plan.open_questions],
                    strawman_proposals=[p.model_dump() for p in plan.strawman_proposals],
                    execution_graph=[s.model_dump() for s in plan.execution_graph],
                    final_output=plan.final_output
                )
                db_session.add(db_plan)

            db_session.commit()
        finally:
            db_session.close()

    def _db_to_plan(self, db_plan: DBSession) -> Plan:
        from .models.plan import OpenQuestion, StrawmanProposal, ExecutionStep

        return Plan(
            session_id=db_plan.id,
            status=PlanStatus(db_plan.status),
            user_intent=db_plan.user_intent,
            scenario_name=db_plan.scenario_name,
            locked_constraints=db_plan.locked_constraints or {},
            open_questions=[OpenQuestion(**q) for q in (db_plan.open_questions or [])],
            strawman_proposals=[StrawmanProposal(**p) for p in (db_plan.strawman_proposals or [])],
            execution_graph=[ExecutionStep(**s) for s in (db_plan.execution_graph or [])],
            final_output=db_plan.final_output
        )
