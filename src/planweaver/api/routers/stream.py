from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from ...db.repositories import PlanRepository
import asyncio
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["stream"])

@router.get("/{session_id}/stream")
async def stream_execution(session_id: str, request: Request):
    """
    Stream execution progress updates via Server-Sent Events.
    """
    repo = PlanRepository()
    plan = repo.get(session_id)

    if not plan:
        return StreamingResponse(
            _error_event("Session not found"),
            media_type="text/event-stream"
        )

    async def event_generator():
        """Yield SSE events as execution progresses"""
        try:
            # Send initial event
            yield _sse_event("connected", {"session_id": session_id})

            # Poll for updates (in production, use proper event queue)
            last_step_count = 0
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from session {session_id}")
                    break

                # Reload plan to check for updates
                plan = repo.get(session_id)
                if not plan:
                    yield _error_event("Session not found")
                    break

                current_steps = len(plan.execution_graph)
                completed = [s for s in plan.execution_graph if s.status.value == "COMPLETED"]
                failed = [s for s in plan.execution_graph if s.status.value == "FAILED"]

                # Check for new completed steps
                if len(completed) > last_step_count:
                    for step in completed[last_step_count:]:
                        yield _sse_event("step_completed", {
                            "step_id": step.step_id,
                            "task": step.task,
                            "output": step.output
                        })
                    last_step_count = len(completed)

                # Check for failures
                if failed:
                    for step in failed:
                        yield _sse_event("step_failed", {
                            "step_id": step.step_id,
                            "error": step.error
                        })
                    break

                # Check if execution complete
                if plan.status.value == "COMPLETED":
                    yield _sse_event("execution_complete", {
                        "total_steps": current_steps,
                        "completed": len(completed)
                    })
                    break

                if plan.status.value == "FAILED":
                    yield _sse_event("execution_failed", {
                        "reason": "Execution failed"
                    })
                    break

                # Wait before polling again
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.exception(f"Error in SSE stream for session {session_id}")
            yield _error_event(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

def _sse_event(event_type: str, data: dict) -> str:
    """Format SSE event"""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

def _error_event(message: str) -> str:
    """Format error event"""
    return _sse_event("error", {"message": message})
