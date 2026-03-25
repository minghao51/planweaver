"""
MCP Server for Agent Communication

Exposes core session operations as MCP tools for external AI agents.
"""

from __future__ import annotations

import json
import logging
import inspect
from typing import Dict, Any, Optional, Literal, cast

from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn

from .models.plan import PlanStatus
from .models.session import SessionMessage, SessionState
from .session import SessionStateMachine
from .negotiator import Negotiator
from .api.serializers import serialize_plan_detail
from .db.database import SessionLocal
from .db.models import SessionMessageModel


logger = logging.getLogger(__name__)


class MCPServer:
    """
    MCP (Model Context Protocol) Server for PlanWeaver.

    Exposes core planning operations as JSON-RPC 2.0 tools for external AI agents.
    """

    def __init__(self, orchestrator):
        """
        Initialize MCP server.

        Args:
            orchestrator: PlanWeaver Orchestrator instance
        """
        self.orchestrator = orchestrator
        self.tools = self._register_tools()

    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register available MCP tools."""
        return {
            "create_session": {
                "name": "create_session",
                "description": "Create a new planning session with user intent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_intent": {
                            "type": "string",
                            "description": "The user's planning intent or goal",
                        },
                        "scenario_name": {
                            "type": "string",
                            "description": "Optional scenario name to guide planning",
                        },
                        "planner_model": {
                            "type": "string",
                            "description": "Optional planner model override",
                        },
                        "executor_model": {
                            "type": "string",
                            "description": "Optional executor model override",
                        },
                    },
                    "required": ["user_intent"],
                },
            },
            "send_message": {
                "name": "send_message",
                "description": "Send a message to a planning session",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The session identifier",
                        },
                        "content": {
                            "type": "string",
                            "description": "Message content to send",
                        },
                        "role": {
                            "type": "string",
                            "enum": ["user", "assistant"],
                            "description": "Message role (default: user)",
                        },
                    },
                    "required": ["session_id", "content"],
                },
            },
            "get_session_state": {
                "name": "get_session_state",
                "description": "Get the current state of a planning session",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The session identifier",
                        },
                    },
                    "required": ["session_id"],
                },
            },
            "approve_plan": {
                "name": "approve_plan",
                "description": "Approve the current plan for execution",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The session identifier",
                        },
                    },
                    "required": ["session_id"],
                },
            },
            "list_sessions": {
                "name": "list_sessions",
                "description": "List all planning sessions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of sessions to return",
                            "default": 50,
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter by status",
                        },
                    },
                },
            },
            "get_similar_plans": {
                "name": "get_similar_plans",
                "description": "Search for similar historical plans",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The session identifier",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 5,
                        },
                    },
                    "required": ["session_id"],
                },
            },
        }

    async def create_session_tool(
        self,
        user_intent: str,
        scenario_name: Optional[str] = None,
        planner_model: Optional[str] = None,
        executor_model: Optional[str] = None,
    ) -> str:
        """
        Create a new planning session.

        Args:
            user_intent: The user's planning intent
            scenario_name: Optional scenario name
            planner_model: Optional planner model
            executor_model: Optional executor model

        Returns:
            JSON string with session creation result
        """
        try:
            plan = None
            start_session_async = getattr(self.orchestrator, "start_session_async", None)
            if callable(start_session_async):
                result = start_session_async(
                    user_intent=user_intent,
                    scenario_name=scenario_name,
                    planner_model=planner_model,
                    executor_model=executor_model,
                )
                if inspect.isawaitable(result):
                    plan = await result
            if plan is None:
                plan = self.orchestrator.start_session(
                    user_intent=user_intent,
                    scenario_name=scenario_name,
                    planner_model=planner_model,
                    executor_model=executor_model,
                )

            open_questions = getattr(plan, "open_questions", [])
            if not isinstance(open_questions, list):
                open_questions = []

            return json.dumps(
                {
                    "success": True,
                    "session_id": plan.session_id,
                    "status": plan.status.value,
                    "user_intent": plan.user_intent,
                    "open_questions": len(open_questions),
                    "created_at": plan.created_at.isoformat(),
                }
            )

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    async def send_message_tool(
        self,
        session_id: str,
        content: str,
        role: str = "user",
    ) -> str:
        """
        Send a message to a planning session.

        Args:
            session_id: The session identifier
            content: Message content
            role: Message role (user/assistant)

        Returns:
            JSON string with message result
        """
        try:
            plan = self.orchestrator.get_session(session_id)
            if not plan:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Session {session_id} not found",
                    }
                )

            metadata = getattr(plan, "metadata", {})
            open_questions = getattr(plan, "open_questions", [])
            if not isinstance(metadata, dict) or not isinstance(open_questions, list):
                return json.dumps(
                    {
                        "success": True,
                        "session_id": session_id,
                        "message": "Message received",
                        "plan_status": plan.status.value,
                    }
                )

            current_state = self._plan_status_to_session_state(plan)
            state_machine = SessionStateMachine(session_id, current_state)
            self._restore_convergence_state(state_machine, plan)

            negotiator = Negotiator()
            message_history = self._get_message_history(session_id)
            output = await negotiator.process(
                message=content,
                plan=plan,
                session_state=state_machine.get_state(),
                message_history=message_history,
            )

            had_mutation = len(output.mutations) > 0
            if output.mutations:
                plan = negotiator.apply_mutations(output.mutations, plan)

            if output.state_transition:
                transition_event = self._session_transition_event(
                    state_machine.get_state(),
                    output.state_transition,
                    output.intent,
                )
                if transition_event:
                    state_machine.transition(transition_event, {"mutations": len(output.mutations)})
                plan.status = self._session_state_to_plan_status(plan.status, output.state_transition)
            else:
                state_machine.record_negotiation_round(had_mutation)

            self._save_session_message(
                SessionMessage(
                    session_id=session_id,
                    role=cast(
                        Literal["user", "assistant", "system"],
                        role if role in {"user", "assistant", "system"} else "user",
                    ),
                    content=content,
                    intent=output.intent,
                )
            )
            self._save_session_message(
                SessionMessage(
                    session_id=session_id,
                    role="assistant",
                    content=output.response_message,
                    intent=output.intent,
                    metadata={
                        "state_transition": output.state_transition.value if output.state_transition else None,
                        "mutations_applied": len(output.mutations),
                    },
                )
            )

            self._persist_convergence_state(state_machine, plan)
            self.orchestrator.plan_repository.save(plan)

            response = {
                "success": True,
                "session_id": session_id,
                "message": output.response_message,
                "intent": output.intent.value,
                "plan_status": plan.status.value,
                "state": state_machine.get_state().value,
                "session": serialize_plan_detail(plan),
            }

            return json.dumps(response)

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    async def get_session_state_tool(self, session_id: str) -> str:
        """
        Get the current state of a planning session.

        Args:
            session_id: The session identifier

        Returns:
            JSON string with session state
        """
        try:
            plan = self.orchestrator.get_session(session_id)
            if not plan:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Session {session_id} not found",
                    }
                )

            state = {
                "success": True,
                "session_id": plan.session_id,
                "status": plan.status.value,
                "user_intent": plan.user_intent,
                "scenario_name": plan.scenario_name,
                "open_questions": len(plan.open_questions),
                "candidate_count": len(plan.candidate_plans),
                "selected_candidate_id": plan.selected_candidate_id,
                "approved_candidate_id": plan.approved_candidate_id,
                "step_count": len(plan.execution_graph),
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat(),
            }

            return json.dumps(state)

        except Exception as e:
            logger.error(f"Failed to get session state: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    async def approve_plan_tool(self, session_id: str) -> str:
        """
        Approve the current plan for execution.

        Args:
            session_id: The session identifier

        Returns:
            JSON string with approval result
        """
        try:
            plan = self.orchestrator.get_session(session_id)
            if not plan:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Session {session_id} not found",
                    }
                )

            updated_plan = self.orchestrator.approve_plan(plan)

            return json.dumps(
                {
                    "success": True,
                    "session_id": session_id,
                    "status": updated_plan.status.value,
                    "approved_candidate_id": updated_plan.approved_candidate_id,
                    "step_count": len(updated_plan.execution_graph),
                }
            )

        except Exception as e:
            logger.error(f"Failed to approve plan: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    async def list_sessions_tool(
        self,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> str:
        """
        List all planning sessions.

        Args:
            limit: Maximum number of sessions
            status: Optional status filter

        Returns:
            JSON string with sessions list
        """
        try:
            result = self.orchestrator.list_sessions(
                limit=limit,
                offset=0,
                status=status,
            )

            sessions = []
            for session in result.get("sessions", []):
                sessions.append(
                    {
                        "session_id": session.session_id,
                        "status": session.status.value,
                        "user_intent": session.user_intent,
                        "created_at": session.created_at.isoformat(),
                    }
                )

            return json.dumps(
                {
                    "success": True,
                    "sessions": sessions,
                    "total": result.get("total", 0),
                    "limit": limit,
                }
            )

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    async def get_similar_plans_tool(
        self,
        session_id: str,
        query: Optional[str] = None,
        limit: int = 5,
    ) -> str:
        """
        Search for similar historical plans.

        Args:
            session_id: The session identifier
            query: Optional search query
            limit: Maximum number of results

        Returns:
            JSON string with similar plans
        """
        try:
            plan = self.orchestrator.get_session(session_id)
            if not plan:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Session {session_id} not found",
                    }
                )

            search_query = query or plan.user_intent

            results = await self.orchestrator.search_similar_plans(
                query=search_query,
                limit=limit,
                similarity_threshold=0.7,
            )

            return json.dumps(
                {
                    "success": True,
                    "session_id": session_id,
                    "query": search_query,
                    "similar_plans": results,
                    "count": len(results),
                }
            )

        except Exception as e:
            logger.error(f"Failed to get similar plans: {e}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    def create_server(self):
        """
        Create and return the MCP server instance.

        Returns:
            Server configuration and tools
        """
        return {
            "name": "planweaver-mcp-server",
            "version": "0.1.0",
            "tools": self.tools,
        }

    def create_app(self) -> FastAPI:
        app = FastAPI(title="PlanWeaver MCP Server", version="0.1.0")

        @app.get("/health")
        async def health() -> Dict[str, Any]:
            return {"status": "healthy", "server": "planweaver-mcp"}

        @app.get("/tools")
        async def tools() -> Dict[str, Any]:
            return self.create_server()

        @app.post("/rpc")
        async def rpc(request: MCPRequest) -> Dict[str, Any]:
            return json.loads(await self.handle_request(request.model_dump()))

        return app

    async def handle_request(self, request: Dict[str, Any]) -> str:
        """
        Handle incoming JSON-RPC 2.0 request.

        Args:
            request: JSON-RPC request dictionary

        Returns:
            JSON-RPC response string
        """
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")

            # Map method names to tool functions
            tool_map: Dict[str, Any] = {
                "create_session": self.create_session_tool,
                "send_message": self.send_message_tool,
                "get_session_state": self.get_session_state_tool,
                "approve_plan": self.approve_plan_tool,
                "list_sessions": self.list_sessions_tool,
                "get_similar_plans": self.get_similar_plans_tool,
            }

            if method not in tool_map:
                return json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32601,
                            "message": "Method not found",
                        },
                        "id": request_id,
                    }
                )

            # Call the tool function
            result = await tool_map[method](**params)

            return json.dumps(
                {
                    "jsonrpc": "2.0",
                    "result": json.loads(result),
                    "id": request_id,
                }
            )

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return json.dumps(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e),
                    },
                    "id": request.get("id"),
                }
            )

    async def run(self, host: str = "localhost", port: int = 8001):
        """
        Run the MCP server.

        Args:
            host: Server host
            port: Server port
        """
        logger.info(f"Starting MCP server on {host}:{port}")
        uvicorn.run(self.create_app(), host=host, port=port)

    def _get_message_history(self, session_id: str) -> list[dict[str, Any]]:
        db = SessionLocal()
        try:
            messages = (
                db.query(SessionMessageModel)
                .filter(SessionMessageModel.session_id == session_id)
                .order_by(SessionMessageModel.created_at.asc())
                .all()
            )
            return [m.to_dict() for m in messages]
        finally:
            db.close()

    def _save_session_message(self, message: SessionMessage) -> None:
        db = SessionLocal()
        try:
            db_message = SessionMessageModel(
                id=message.id,
                session_id=message.session_id,
                role=message.role,
                content=message.content,
                intent=message.intent.value if message.intent else None,
                extra_data=message.metadata,
            )
            db.add(db_message)
            db.commit()
        finally:
            db.close()

    def _plan_status_to_session_state(self, plan) -> SessionState:
        if plan.status == PlanStatus.EXECUTING:
            return SessionState.EXECUTING
        if plan.status in {PlanStatus.COMPLETED, PlanStatus.FAILED}:
            return SessionState.DONE
        if plan.status in {PlanStatus.AWAITING_APPROVAL, PlanStatus.APPROVED}:
            return SessionState.NEGOTIATING
        if any(not question.answered for question in plan.open_questions):
            return SessionState.CLARIFYING
        return SessionState.PLANNING

    def _session_transition_event(self, current_state: SessionState, next_state: SessionState, intent) -> Optional[str]:
        direct_mapping = {
            (SessionState.GOAL_RECEIVED, SessionState.CLARIFYING): "start_clarifying",
            (SessionState.GOAL_RECEIVED, SessionState.PLANNING): "start_planning",
            (SessionState.CLARIFYING, SessionState.PLANNING): "all_questions_answered",
            (SessionState.PLANNING, SessionState.NEGOTIATING): "plan_ready",
            (SessionState.NEGOTIATING, SessionState.PLANNING): "request_revision",
            (SessionState.NEGOTIATING, SessionState.EXECUTING): "approve",
            (SessionState.EXECUTING, SessionState.DONE): "execution_complete",
        }
        if next_state == SessionState.DONE:
            return "cancel"
        if current_state == next_state:
            return None
        intent_mapping = {
            "approve": "approve",
            "reject": "cancel",
            "execute": "approve",
            "answer": "all_questions_answered",
            "revise": "request_revision",
        }
        return direct_mapping.get((current_state, next_state), intent_mapping.get(intent.value, "request_revision"))

    def _session_state_to_plan_status(self, current_status: PlanStatus, next_state: SessionState) -> PlanStatus:
        if next_state in {SessionState.GOAL_RECEIVED, SessionState.CLARIFYING, SessionState.PLANNING}:
            return PlanStatus.BRAINSTORMING
        if next_state == SessionState.NEGOTIATING:
            return PlanStatus.AWAITING_APPROVAL
        if next_state == SessionState.EXECUTING:
            return PlanStatus.APPROVED
        return current_status

    def _restore_convergence_state(self, state_machine: SessionStateMachine, plan) -> None:
        counters = plan.metadata.get("negotiation_convergence")
        if not isinstance(counters, dict):
            return
        rounds_without_change = counters.get("rounds_without_change", 0)
        last_mutation_round = counters.get("last_mutation_round", 0)
        if isinstance(rounds_without_change, int) and isinstance(last_mutation_round, int):
            state_machine.load_convergence_state(rounds_without_change, last_mutation_round)

    def _persist_convergence_state(self, state_machine: SessionStateMachine, plan) -> None:
        if state_machine.get_state() == SessionState.NEGOTIATING:
            plan.metadata["negotiation_convergence"] = state_machine.dump_convergence_state()
        else:
            plan.metadata.pop("negotiation_convergence", None)


class MCPRequest(BaseModel):
    """MCP JSON-RPC 2.0 request model."""

    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: Optional[str] = None


class MCPResponse(BaseModel):
    """MCP JSON-RPC 2.0 response model."""

    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPError(BaseModel):
    """MCP error model."""

    code: int
    message: str
    data: Optional[Any] = None
