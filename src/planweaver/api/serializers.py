from ..models.plan import Plan


def _list_attr(plan: object, name: str) -> list:
    value = getattr(plan, name, [])
    return value if isinstance(value, list) else []


def _optional_str_attr(plan: object, name: str) -> str | None:
    value = getattr(plan, name, None)
    return value if isinstance(value, str) else None


def _optional_payload_attr(plan: object, name: str):
    value = getattr(plan, name, None)
    return value if isinstance(value, (dict, list, str, int, float, bool)) or value is None else None


def serialize_plan_summary(plan: Plan) -> dict:
    return {
        "session_id": plan.session_id,
        "status": plan.status.value,
        "open_questions": [q.model_dump() for q in _list_attr(plan, "open_questions")],
        "selected_candidate_id": _optional_str_attr(plan, "selected_candidate_id"),
        "approved_candidate_id": _optional_str_attr(plan, "approved_candidate_id"),
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
        "open_questions": [q.model_dump() for q in _list_attr(plan, "open_questions")],
        "strawman_proposals": [p.model_dump() for p in _list_attr(plan, "strawman_proposals")],
        "execution_graph": [s.model_dump() for s in _list_attr(plan, "execution_graph")],
        "external_contexts": [c.model_dump(mode="json") for c in _list_attr(plan, "external_contexts")],
        "context_suggestions": [s.model_dump(mode="json") for s in _list_attr(plan, "context_suggestions")],
        "candidate_plans": [c.model_dump(mode="json") for c in _list_attr(plan, "candidate_plans")],
        "candidate_revisions": [r.model_dump(mode="json") for r in _list_attr(plan, "candidate_revisions")],
        "planning_outcomes": [o.model_dump(mode="json") for o in _list_attr(plan, "planning_outcomes")],
        "selected_candidate_id": _optional_str_attr(plan, "selected_candidate_id"),
        "approved_candidate_id": _optional_str_attr(plan, "approved_candidate_id"),
        "final_output": _optional_payload_attr(plan, "final_output"),
    }


def serialize_execution_graph(plan: Plan) -> list[dict]:
    return [s.model_dump() for s in plan.execution_graph]
