from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.exc import OperationalError

from .database import ensure_db_ready, get_session
from .models import SessionModel as DBSession
from ..config import get_settings
from ..models.plan import (
    CandidatePlan,
    CandidatePlanRevision,
    ContextSuggestion,
    ExecutionStep,
    ExternalContext,
    OpenQuestion,
    Plan,
    PlanStatus,
    PlanningOutcome,
    StrawmanProposal,
)

PLANNER_OVERRIDE_KEY = "__planner_model_override__"
EXECUTOR_OVERRIDE_KEY = "__executor_model_override__"


class PlanRepository:
    def __init__(self, db_session=None):
        self._db_session = db_session
        self._settings = get_settings()

    def list_summaries(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        query: Optional[str] = None,
    ) -> dict:
        for attempt in range(2):
            ensure_db_ready(force=attempt > 0)
            db_session = self._db_session or get_session()
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
                rows = db_query.order_by(DBSession.updated_at.desc()).offset(offset).limit(limit).all()
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
            except OperationalError as exc:
                if attempt == 0 and "no such table" in str(exc).lower():
                    continue
                raise
            finally:
                if self._db_session is not db_session:
                    db_session.close()

    def get(self, session_id: str) -> Optional[Plan]:
        for attempt in range(2):
            ensure_db_ready(force=attempt > 0)
            db_session = self._db_session or get_session()
            try:
                db_plan = db_session.query(DBSession).filter_by(id=session_id).first()
                if not db_plan:
                    return None
                return self._db_to_plan(db_plan)
            except OperationalError as exc:
                if attempt == 0 and "no such table" in str(exc).lower():
                    continue
                raise
            finally:
                if self._db_session is not db_session:
                    db_session.close()

    def save(self, plan: Plan) -> None:
        for attempt in range(2):
            ensure_db_ready(force=attempt > 0)
            db_session = self._db_session or get_session()
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
                return
            except OperationalError as exc:
                if self._db_session is not db_session:
                    db_session.rollback()
                if attempt == 0 and "no such table" in str(exc).lower():
                    continue
                raise
            finally:
                if self._db_session is not db_session:
                    db_session.close()

    def _plan_to_db_payload(self, plan: Plan) -> dict:
        locked_constraints = dict(plan.locked_constraints)
        if plan.planner_model:
            locked_constraints[PLANNER_OVERRIDE_KEY] = plan.planner_model
        if plan.executor_model:
            locked_constraints[EXECUTOR_OVERRIDE_KEY] = plan.executor_model

        expires_at = None
        if self._settings.session_ttl_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=self._settings.session_ttl_days)

        return {
            "user_intent": plan.user_intent,
            "scenario_name": plan.scenario_name,
            "status": plan.status.value,
            "locked_constraints": locked_constraints,
            "open_questions": self._model_dump_list(plan.open_questions),
            "strawman_proposals": self._model_dump_list(plan.strawman_proposals),
            "execution_graph": self._model_dump_list(plan.execution_graph),
            "external_contexts": self._model_dump_list(plan.external_contexts, mode="json"),
            "candidate_plans": self._model_dump_list(plan.candidate_plans, mode="json"),
            "candidate_revisions": self._model_dump_list(plan.candidate_revisions, mode="json"),
            "planning_outcomes": self._model_dump_list(plan.planning_outcomes, mode="json"),
            "context_suggestions": self._model_dump_list(plan.context_suggestions, mode="json"),
            "selected_candidate_id": plan.selected_candidate_id,
            "approved_candidate_id": plan.approved_candidate_id,
            "session_metadata": dict(plan.metadata),
            "expires_at": expires_at,
            "final_output": plan.final_output,
        }

    def _model_dump_list(self, value, mode: Optional[str] = None) -> list:
        if not isinstance(value, list):
            return []
        dumped = []
        for item in value:
            if hasattr(item, "model_dump"):
                kwargs = {"mode": mode} if mode else {}
                dumped.append(item.model_dump(**kwargs))
            else:
                dumped.append(item)
        return dumped

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
            candidate_plans=[CandidatePlan(**c) for c in (db_plan.candidate_plans or [])],
            candidate_revisions=[CandidatePlanRevision(**r) for r in (db_plan.candidate_revisions or [])],
            planning_outcomes=[PlanningOutcome(**o) for o in (db_plan.planning_outcomes or [])],
            context_suggestions=[ContextSuggestion(**s) for s in (db_plan.context_suggestions or [])],
            selected_candidate_id=db_plan.selected_candidate_id,
            approved_candidate_id=db_plan.approved_candidate_id,
            planner_model=planner_model,
            executor_model=executor_model,
            metadata=dict(db_plan.session_metadata or {}),
            final_output=db_plan.final_output,
        )
