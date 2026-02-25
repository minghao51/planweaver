from fastapi import APIRouter, File, HTTPException, UploadFile

from ..dependencies import get_context_service, get_plan_or_404
from ..schemas import GitHubContextRequest, WebSearchContextRequest

router = APIRouter()


@router.post("/sessions/{session_id}/context/github")
async def add_github_context(session_id: str, request: GitHubContextRequest):
    orch, _ = get_plan_or_404(session_id)
    context_service = get_context_service()

    try:
        context = await context_service.add_github_context(request.repo_url)
        orch.add_external_context(session_id, context)
        return {
            "context_id": context.id,
            "source_type": context.source_type,
            "status": "added",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to add GitHub context: {exc}"
        ) from exc


@router.post("/sessions/{session_id}/context/web-search")
async def add_web_search_context(session_id: str, request: WebSearchContextRequest):
    orch, plan = get_plan_or_404(session_id)
    context_service = get_context_service()

    try:
        query = request.query or f"best practices for: {plan.user_intent}"
        context = await context_service.add_web_search_context(query)
        orch.add_external_context(session_id, context)
        return {
            "context_id": context.id,
            "source_type": context.source_type,
            "query": query,
            "status": "added",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to add web search: {exc}"
        ) from exc


@router.post("/sessions/{session_id}/context/upload")
async def upload_file_context(
    session_id: str,
    file: UploadFile = File(..., description="File to upload for context"),
):
    orch, _ = get_plan_or_404(session_id)
    context_service = get_context_service()

    try:
        content = await file.read()
        context = await context_service.add_file_context(file.filename, content)
        orch.add_external_context(session_id, context)
        return {
            "context_id": context.id,
            "source_type": context.source_type,
            "filename": file.filename,
            "status": "added",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to process file: {exc}"
        ) from exc


@router.get("/sessions/{session_id}/context")
def list_contexts(session_id: str):
    _, plan = get_plan_or_404(session_id)
    return {
        "session_id": session_id,
        "contexts": [
            {
                "id": ctx.id,
                "source_type": ctx.source_type,
                "source_url": ctx.source_url,
                "created_at": ctx.created_at,
                "metadata": {
                    key: value
                    for key, value in ctx.metadata.items()
                    if key != "full_content"
                },
            }
            for ctx in plan.external_contexts
        ],
    }
