import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient

from src.planweaver.models.plan import ExecutionStep, Plan, PlanStatus
from src.planweaver.models.session import NegotiatorIntent, NegotiatorOutput, SessionState
from src.planweaver.api.routers.sessions import _session_transition_event


class TestAPI:
    @pytest.fixture
    def mock_orchestrator(self):
        with patch("src.planweaver.api.routers.sessions.get_orchestrator") as mock_get:
            orchestrator = Mock()
            orchestrator.start_session_async = None
            orchestrator.start_session = Mock(
                return_value=Mock(
                    session_id="test-123",
                    status=Mock(value="brainstorming"),
                    open_questions=[],
                    selected_candidate_id=None,
                    approved_candidate_id=None,
                    metadata={},
                )
            )
            orchestrator.get_session = Mock(
                return_value=Mock(
                    session_id="test-123",
                    status=Mock(value="brainstorming"),
                    user_intent="test intent",
                    locked_constraints={},
                    open_questions=[],
                    strawman_proposals=[],
                    execution_graph=[],
                    external_contexts=[],
                    context_suggestions=[],
                    candidate_plans=[],
                    candidate_revisions=[],
                    planning_outcomes=[],
                    selected_candidate_id=None,
                    approved_candidate_id=None,
                    metadata={},
                    final_output=None,
                )
            )
            mock_get.return_value = orchestrator
            yield orchestrator

    @pytest.fixture
    def client(self, mock_orchestrator):
        with patch(
            "src.planweaver.api.routers.sessions.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            with patch("src.planweaver.api.main.init_db"):
                from src.planweaver.api.main import app

                return TestClient(app)

    def test_create_session_requires_user_intent(self):
        with patch("src.planweaver.api.routers.sessions.get_orchestrator") as mock_get:
            mock_orch = Mock()
            mock_get.return_value = mock_orch

            from src.planweaver.api.main import app

            client = TestClient(app)

            response = client.post("/api/v1/sessions", json={})
            assert response.status_code == 422

    def test_create_session_returns_session_id(self, mock_orchestrator):
        from src.planweaver.api.main import app

        client = TestClient(app)

        with patch(
            "src.planweaver.api.routers.sessions.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            response = client.post("/api/v1/sessions", json={"user_intent": "Create a web app"})

            assert response.status_code == 200
            assert "session_id" in response.json()

    def test_create_session_uses_sync_start_session_async_result(self):
        from src.planweaver.api.main import app

        client = TestClient(app)
        sync_plan = Mock(
            session_id="test-123",
            status=Mock(value="brainstorming"),
            open_questions=[],
            selected_candidate_id=None,
            approved_candidate_id=None,
            metadata={},
        )

        with patch("src.planweaver.api.routers.sessions.get_orchestrator") as mock_get:
            mock_orch = Mock()
            mock_orch.start_session_async = Mock(return_value=sync_plan)
            mock_orch.start_session = Mock()
            mock_get.return_value = mock_orch

            response = client.post("/api/v1/sessions", json={"user_intent": "Create a web app"})

            assert response.status_code == 200
            assert response.json()["session_id"] == "test-123"
            mock_orch.start_session.assert_not_called()

    def test_get_session_not_found(self):
        with patch("src.planweaver.api.routers.sessions.get_orchestrator") as mock_get:
            mock_orch = Mock()
            mock_orch.get_session.return_value = None
            mock_get.return_value = mock_orch

            from src.planweaver.api.main import app

            client = TestClient(app)

            response = client.get("/api/v1/sessions/nonexistent")
            assert response.status_code == 404

    def test_list_models_returns_models(self, mock_orchestrator):
        from src.planweaver.api.main import app

        client = TestClient(app)

        mock_orchestrator.llm.get_available_models.return_value = [
            {"id": "gemini-3-pro-preview", "name": "Gemini 3 Pro", "type": "planner"}
        ]

        with patch(
            "src.planweaver.api.routers.metadata.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            response = client.get("/api/v1/models")

            assert response.status_code == 200
            assert "models" in response.json()
            models = response.json()["models"]
            assert any("gemini" in m["id"].lower() for m in models)

    def test_list_scenarios_returns_scenarios(self, mock_orchestrator):
        from src.planweaver.api.main import app

        client = TestClient(app)

        mock_orchestrator.template_engine.list_scenarios.return_value = [
            {"name": "test_scenario", "description": "A test"}
        ]

        with patch(
            "src.planweaver.api.routers.metadata.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            response = client.get("/api/v1/scenarios")

            assert response.status_code == 200
            assert "scenarios" in response.json()

    def test_list_sessions_returns_history(self):
        from src.planweaver.api.main import app

        client = TestClient(app)

        sessions = {
            "sessions": [
                {
                    "session_id": "proj_abc123",
                    "status": "COMPLETED",
                    "user_intent": "Refactor CLI into API",
                    "scenario_name": None,
                    "created_at": "2026-02-25T10:00:00+00:00",
                    "updated_at": "2026-02-25T10:05:00+00:00",
                }
            ],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }

        with patch("src.planweaver.api.routers.sessions.get_orchestrator") as mock_get:
            mock_orch = Mock()
            mock_orch.list_sessions.return_value = sessions
            mock_get.return_value = mock_orch

            response = client.get("/api/v1/sessions")

            assert response.status_code == 200
            payload = response.json()
            assert "sessions" in payload
            assert payload["sessions"][0]["session_id"] == "proj_abc123"
            assert payload["total"] == 1
            assert payload["offset"] == 0


class TestAPIValidation:
    def test_sessions_endpoint_requires_user_intent(self):
        from src.planweaver.api.main import app

        client = TestClient(app)

        response = client.post("/api/v1/sessions", json={})
        assert response.status_code == 422

    def test_execute_requires_approved_plan(self):
        with patch("src.planweaver.api.dependencies.get_orchestrator") as mock_get:
            from src.planweaver.models.plan import PlanStatus

            mock_orch = Mock()
            mock_plan = Mock()
            mock_plan.status = PlanStatus.BRAINSTORMING
            mock_orch.get_session.return_value = mock_plan
            mock_get.return_value = mock_orch

            from src.planweaver.api.main import app

            client = TestClient(app)

            response = client.post("/api/v1/sessions/test-123/execute", json={})
            assert response.status_code == 400

    def test_approve_returns_validation_errors_as_400(self):
        with patch("src.planweaver.api.routers.sessions.get_plan_or_404") as mock_get_plan:
            mock_orch = Mock()
            mock_plan = Mock()
            mock_plan.execution_graph = [Mock()]
            mock_orch.approve_plan.side_effect = ValueError("critic blocked approval")
            mock_get_plan.return_value = (mock_orch, mock_plan)

            from src.planweaver.api.main import app

            client = TestClient(app)

            response = client.post("/api/v1/sessions/test-123/approve")
            assert response.status_code == 400
            assert response.json()["detail"] == "critic blocked approval"

    def test_optimizer_accepts_short_proposal_ids(self):
        from src.planweaver.api.main import app

        client = TestClient(app)

        with patch("src.planweaver.api.routers.optimizer.get_session") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            with patch("src.planweaver.api.routers.optimizer.OptimizerService") as mock_service_cls:
                mock_service = Mock()
                mock_service.optimize_plan.return_value = {
                    "status": "completed",
                    "variants": [],
                    "ratings": {},
                }
                mock_service_cls.return_value = mock_service

                response = client.post(
                    "/api/v1/optimizer/optimize",
                    json={"selected_proposal_id": "1"},
                )

                assert response.status_code == 200

    def test_done_transition_prefers_execution_complete_over_cancel(self):
        event = _session_transition_event(
            SessionState.EXECUTING,
            SessionState.DONE,
            NegotiatorIntent.APPROVE,
        )

        assert event == "execution_complete"

    def test_manual_plan_endpoint_returns_normalized_plan(self):
        from src.planweaver.api.main import app

        client = TestClient(app)

        mocked_response = {
            "normalized_plan": {
                "id": "plan-manual-1",
                "session_id": None,
                "source_type": "manual",
                "source_model": "human",
                "planning_style": "manual",
                "title": "Manual migration plan",
                "summary": "Move the service safely",
                "assumptions": [],
                "constraints": [],
                "success_criteria": [],
                "risks": [],
                "fallbacks": [],
                "estimated_time_minutes": None,
                "estimated_cost_usd": None,
                "steps": [
                    {
                        "step_id": "step-1",
                        "description": "Audit the current schema",
                        "dependencies": [],
                        "validation": [],
                        "tools": [],
                        "owner_model": None,
                        "estimated_time_minutes": None,
                    }
                ],
                "metadata": {},
                "normalization_warnings": ["Missing explicit success criteria."],
            },
            "evaluations": {
                "judge-a": {
                    "plan_id": "plan-manual-1",
                    "judge_model": "judge-a",
                    "rubric_scores": {"completeness": 7.0},
                    "overall_score": 7.0,
                    "strengths": [],
                    "weaknesses": [],
                    "blocking_issues": [],
                    "confidence": 0.7,
                    "verdict": "acceptable",
                }
            },
            "ranking": [
                {
                    "plan_id": "plan-manual-1",
                    "final_score": 7.0,
                    "rank": 1,
                    "confidence": 0.7,
                    "disagreement_level": "low",
                    "recommendation_reason": "Recommended because it shows balanced rubric performance.",
                }
            ],
        }

        with patch("src.planweaver.api.routers.optimizer.get_optimizer_service") as mock_get_service:
            mock_service = Mock()
            mock_service.submit_manual_plan.return_value = mocked_response
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/optimizer/manual",
                json={
                    "title": "Manual migration plan",
                    "plan_text": "Audit the current schema",
                },
            )

        assert response.status_code == 200

    def test_message_endpoint_handles_brainstorming_plan_status(self):
        from src.planweaver.api.main import app

        client = TestClient(app)
        plan = Plan(session_id="test-123", user_intent="Refine the rollout", status=PlanStatus.BRAINSTORMING)
        orchestrator = Mock()
        orchestrator.plan_repository.save = Mock()

        with patch("src.planweaver.api.routers.sessions.get_plan_or_404", return_value=(orchestrator, plan)):
            with patch("src.planweaver.api.routers.sessions._get_message_history", return_value=[]):
                with patch("src.planweaver.api.routers.sessions._save_session_message"):
                    with patch("src.planweaver.api.routers.sessions.Negotiator") as mock_negotiator_cls:
                        mock_negotiator = Mock()
                        mock_negotiator.process = AsyncMock(
                            return_value=NegotiatorOutput(
                                intent=NegotiatorIntent.ASK_QUESTION,
                                response_message="What tradeoffs matter most?",
                                mutations=[],
                                state_transition=None,
                            )
                        )
                        mock_negotiator_cls.return_value = mock_negotiator

                        response = client.post(
                            "/api/v1/sessions/test-123/message",
                            json={"content": "What should we optimize for?"},
                        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["state"] == SessionState.PLANNING.value
        assert payload["session"]["status"] == PlanStatus.BRAINSTORMING.value

    def test_message_endpoint_preserves_valid_plan_status_for_done_transition(self):
        from src.planweaver.api.main import app

        client = TestClient(app)
        plan = Plan(session_id="test-123", user_intent="Refine the rollout", status=PlanStatus.AWAITING_APPROVAL)
        orchestrator = Mock()
        orchestrator.plan_repository.save = Mock()

        with patch("src.planweaver.api.routers.sessions.get_plan_or_404", return_value=(orchestrator, plan)):
            with patch("src.planweaver.api.routers.sessions._get_message_history", return_value=[]):
                with patch("src.planweaver.api.routers.sessions._save_session_message"):
                    with patch("src.planweaver.api.routers.sessions.Negotiator") as mock_negotiator_cls:
                        mock_negotiator = Mock()
                        mock_negotiator.process = AsyncMock(
                            return_value=NegotiatorOutput(
                                intent=NegotiatorIntent.REJECT,
                                response_message="Stopping here.",
                                mutations=[],
                                state_transition=SessionState.DONE,
                            )
                        )
                        mock_negotiator_cls.return_value = mock_negotiator

                        response = client.post(
                            "/api/v1/sessions/test-123/message",
                            json={"content": "Cancel this"},
                        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["state"] == SessionState.DONE.value
        assert payload["session"]["status"] == PlanStatus.AWAITING_APPROVAL.value

    def test_message_endpoint_persists_convergence_across_requests(self):
        from src.planweaver.api.main import app

        client = TestClient(app)
        plan = Plan(
            session_id="test-123",
            user_intent="Refine the rollout",
            status=PlanStatus.AWAITING_APPROVAL,
            execution_graph=[
                ExecutionStep(
                    step_id=1,
                    task="Draft the rollout checklist",
                    prompt_template_id="default",
                    assigned_model="test-model",
                )
            ],
        )
        orchestrator = Mock()
        orchestrator.plan_repository.save = Mock()

        with patch("src.planweaver.api.routers.sessions.get_plan_or_404", return_value=(orchestrator, plan)):
            with patch("src.planweaver.api.routers.sessions._get_message_history", return_value=[]):
                with patch("src.planweaver.api.routers.sessions._save_session_message"):
                    with patch("src.planweaver.api.routers.sessions.Negotiator") as mock_negotiator_cls:
                        mock_negotiator = Mock()
                        mock_negotiator.process = AsyncMock(
                            side_effect=[
                                NegotiatorOutput(
                                    intent=NegotiatorIntent.STATUS_QUERY,
                                    response_message="Still waiting for approval.",
                                    mutations=[],
                                    state_transition=None,
                                ),
                                NegotiatorOutput(
                                    intent=NegotiatorIntent.STATUS_QUERY,
                                    response_message="Still waiting for approval.",
                                    mutations=[],
                                    state_transition=None,
                                ),
                            ]
                        )
                        mock_negotiator_cls.return_value = mock_negotiator

                        first = client.post(
                            "/api/v1/sessions/test-123/message",
                            json={"content": "Status?"},
                        )
                        second = client.post(
                            "/api/v1/sessions/test-123/message",
                            json={"content": "Status now?"},
                        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["convergence_status"]["rounds_without_change"] == 1
        assert second.json()["convergence_status"]["rounds_without_change"] == 2

    def test_compare_endpoint_returns_pairwise_comparisons(self):
        from src.planweaver.api.main import app

        client = TestClient(app)

        mocked_response = {
            "normalized_plans": [
                {
                    "id": "plan-a",
                    "session_id": None,
                    "source_type": "llm_generated",
                    "source_model": "planner-a",
                    "planning_style": "baseline",
                    "title": "Plan A",
                    "summary": "Safer rollout",
                    "assumptions": [],
                    "constraints": [],
                    "success_criteria": ["No regressions"],
                    "risks": [],
                    "fallbacks": [],
                    "estimated_time_minutes": 10,
                    "estimated_cost_usd": "0.10",
                    "steps": [],
                    "metadata": {},
                    "normalization_warnings": [],
                },
                {
                    "id": "plan-b",
                    "session_id": None,
                    "source_type": "llm_generated",
                    "source_model": "planner-b",
                    "planning_style": "baseline",
                    "title": "Plan B",
                    "summary": "Faster rollout",
                    "assumptions": [],
                    "constraints": [],
                    "success_criteria": ["Ship quickly"],
                    "risks": [],
                    "fallbacks": [],
                    "estimated_time_minutes": 8,
                    "estimated_cost_usd": "0.05",
                    "steps": [],
                    "metadata": {},
                    "normalization_warnings": [],
                },
            ],
            "evaluations": {},
            "comparisons": [
                {
                    "left_plan_id": "plan-a",
                    "right_plan_id": "plan-b",
                    "judge_model": "aggregate",
                    "winner_plan_id": "plan-a",
                    "margin": "moderate",
                    "rationale": "Plan A is preferred.",
                    "preference_factors": ["verification_quality"],
                }
            ],
            "ranking": [
                {
                    "plan_id": "plan-a",
                    "final_score": 8.1,
                    "rank": 1,
                    "confidence": 0.78,
                    "disagreement_level": "low",
                    "recommendation_reason": "Recommended because it shows verification quality.",
                }
            ],
        }

        with patch("src.planweaver.api.routers.optimizer.get_optimizer_service") as mock_get_service:
            mock_service = Mock()
            mock_service.normalize_plan_payload.side_effect = [
                Mock(
                    model_dump=Mock(return_value=mocked_response["normalized_plans"][0]),
                    id="plan-a",
                ),
                Mock(
                    model_dump=Mock(return_value=mocked_response["normalized_plans"][1]),
                    id="plan-b",
                ),
            ]
            mock_service.evaluate_normalized_plans.return_value = {}
            mock_service.compare_plans.return_value = [
                Mock(model_dump=Mock(return_value=mocked_response["comparisons"][0]))
            ]
            mock_service.rank_plans.return_value = [Mock(model_dump=Mock(return_value=mocked_response["ranking"][0]))]
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/optimizer/compare",
                json={
                    "plans": [
                        {"title": "Plan A", "description": "Safer rollout"},
                        {"title": "Plan B", "description": "Faster rollout"},
                    ]
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["comparisons"][0]["winner_plan_id"] == "plan-a"
