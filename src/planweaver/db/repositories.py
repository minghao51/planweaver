from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_

from .database import get_session
from .models import SessionModel as DBSession
from ..models.plan import (
    ExecutionStep,
    ExternalContext,
    OpenQuestion,
    Plan,
    PlanStatus,
    StrawmanProposal,
)

PLANNER_OVERRIDE_KEY = "__planner_model_override__"
EXECUTOR_OVERRIDE_KEY = "__executor_model_override__"


class PlanRepository:
    def list_summaries(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        query: Optional[str] = None,
    ) -> dict:
        db_session = get_session()
        try:
            db_query = db_session.query(DBSession)

            if status:
                db_query = db_query.filter(DBSession.status == status)

            if query:
                pattern = f"%{query.strip()}%"
                db_query = db_query.filter(
                    or_(
                        DBSession.user_intent.ilike(pattern),
                        DBSession.scenario_name.ilike(pattern),
                    )
                )

            total = db_query.count()
            rows = (
                db_query.order_by(DBSession.updated_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return {
                "sessions": [
                    {
                        "session_id": row.id,
                        "status": row.status,
                        "user_intent": row.user_intent,
                        "scenario_name": row.scenario_name,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    }
                    for row in rows
                ],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        finally:
            db_session.close()

    def get(self, session_id: str) -> Optional[Plan]:
        db_session = get_session()
        try:
            db_plan = db_session.query(DBSession).filter_by(id=session_id).first()
            if not db_plan:
                return None
            return self._db_to_plan(db_plan)
        finally:
            db_session.close()

    def save(self, plan: Plan) -> None:
        db_session = get_session()
        try:
            existing = db_session.query(DBSession).filter_by(id=plan.session_id).first()

            payload = self._plan_to_db_payload(plan)
            if existing:
                for field, value in payload.items():
                    setattr(existing, field, value)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                db_session.add(DBSession(id=plan.session_id, **payload))

            db_session.commit()
        finally:
            db_session.close()

    def _plan_to_db_payload(self, plan: Plan) -> dict:
        locked_constraints = dict(plan.locked_constraints)
        if plan.planner_model:
            locked_constraints[PLANNER_OVERRIDE_KEY] = plan.planner_model
        if plan.executor_model:
            locked_constraints[EXECUTOR_OVERRIDE_KEY] = plan.executor_model

        return {
            "user_intent": plan.user_intent,
            "scenario_name": plan.scenario_name,
            "status": plan.status.value,
            "locked_constraints": locked_constraints,
            "open_questions": [q.model_dump() for q in plan.open_questions],
            "strawman_proposals": [p.model_dump() for p in plan.strawman_proposals],
            "execution_graph": [s.model_dump() for s in plan.execution_graph],
            "external_contexts": [c.model_dump(mode="json") for c in plan.external_contexts],
            "final_output": plan.final_output,
        }

    def _db_to_plan(self, db_plan: DBSession) -> Plan:
        locked_constraints = dict(db_plan.locked_constraints or {})
        planner_model = locked_constraints.pop(PLANNER_OVERRIDE_KEY, None)
        executor_model = locked_constraints.pop(EXECUTOR_OVERRIDE_KEY, None)

        return Plan(
            session_id=db_plan.id,
            status=PlanStatus(db_plan.status),
            user_intent=db_plan.user_intent,
            scenario_name=db_plan.scenario_name,
            locked_constraints=locked_constraints,
            open_questions=[OpenQuestion(**q) for q in (db_plan.open_questions or [])],
            strawman_proposals=[StrawmanProposal(**p) for p in (db_plan.strawman_proposals or [])],
            execution_graph=[ExecutionStep(**s) for s in (db_plan.execution_graph or [])],
            external_contexts=[ExternalContext(**c) for c in (db_plan.external_contexts or [])],
            planner_model=planner_model,
            executor_model=executor_model,
            final_output=db_plan.final_output,
        )
