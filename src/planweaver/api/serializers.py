from ..models.plan import Plan


def serialize_plan_summary(plan: Plan) -> dict:
    return {
        "session_id": plan.session_id,
        "status": plan.status.value,
        "open_questions": [q.model_dump() for q in plan.open_questions],
    }


def serialize_session_history_item(item: dict) -> dict:
    return {
        "session_id": item["session_id"],
        "status": item["status"],
        "user_intent": item["user_intent"],
        "scenario_name": item.get("scenario_name"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def serialize_plan_detail(plan: Plan) -> dict:
    return {
        "session_id": plan.session_id,
        "status": plan.status.value,
        "user_intent": plan.user_intent,
        "locked_constraints": plan.locked_constraints,
        "open_questions": [q.model_dump() for q in plan.open_questions],
        "strawman_proposals": [p.model_dump() for p in plan.strawman_proposals],
        "execution_graph": [s.model_dump() for s in plan.execution_graph],
    }


def serialize_execution_graph(plan: Plan) -> list[dict]:
    return [s.model_dump() for s in plan.execution_graph]
