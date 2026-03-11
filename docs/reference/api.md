# PlanWeaver API Reference

Complete reference for all PlanWeaver API endpoints.

**Base URL:** `http://localhost:8000`

**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)

---

## Table of Contents

- [Sessions](#sessions)
- [External Context](#external-context)
- [Plan Optimizer](#plan-optimizer)
- [Utilities](#utilities)

---

## Sessions

### Create Session

**POST** `/api/v1/sessions`

Creates a new planning session with the provided user intent.

**Request Body:**
```json
{
  "user_intent": "Build a REST API for inventory management",
  "scenario_name": "code_refactoring",
  "planner_model": "gemini-2.5-flash",
  "executor_model": "gemini-3-flash"
}
```

**Response:** `201 Created`
```json
{
  "session_id": "uuid-string",
  "status": "BRAINSTORMING",
  "user_intent": "Build a REST API for inventory management",
  "open_questions": [],
  "locked_constraints": {},
  "external_contexts": [],
  "created_at": "2025-02-28T10:00:00Z"
}
```

**Fields:**
- `user_intent` (required): The user's request or goal
- `scenario_name` (optional): Name of scenario template to use
- `planner_model` (optional): Override default planner model
- `executor_model` (optional): Override default executor model

---

### Get Session

**GET** `/api/v1/sessions/{session_id}`

Retrieves details of a specific session.

**Parameters:**
- `session_id` (path): UUID of the session

**Response:** `200 OK`
```json
{
  "session_id": "uuid-string",
  "status": "APPROVED",
  "user_intent": "...",
  "locked_constraints": {},
  "open_questions": [],
  "strawman_proposals": [],
  "execution_graph": [],
  "external_contexts": [],
  "planner_model": "gemini-2.5-flash",
  "executor_model": "gemini-3-flash",
  "created_at": "2025-02-28T10:00:00Z"
}
```

---

### List Sessions

**GET** `/api/v1/sessions`

Lists all sessions with optional filtering.

**Query Parameters:**
- `limit` (optional, default=50): Maximum number of sessions to return
- `offset` (optional, default=0): Number of sessions to skip
- `status` (optional): Filter by plan status
- `query` (optional): Search term for user_intent

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "session_id": "uuid-string",
      "status": "COMPLETED",
      "user_intent": "...",
      "created_at": "2025-02-28T10:00:00Z"
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

---

### Answer Questions

**POST** `/api/v1/sessions/{session_id}/questions`

Answers clarifying questions from the planner.

**Request Body:**
```json
{
  "answers": {
    "q1": "Use FastAPI",
    "q2": "PostgreSQL for production"
  }
}
```

**Response:** `200 OK`
```json
{
  "session_id": "uuid-string",
  "status": "AWAITING_APPROVAL",
  "open_questions": [
    {
      "id": "q3",
      "question": "...",
      "answered": false
    }
  ]
}
```

---

### Get Proposals

**GET** `/api/v1/sessions/{session_id}/proposals`

Gets strawman proposals for the session.

**Response:** `200 OK`
```json
{
  "proposals": [
    {
      "id": "1",
      "title": "Monolithic Approach",
      "description": "Build as single application...",
      "pros": ["Simpler deployment", "Shared state"],
      "cons": ["Scaling limits", "Tight coupling"],
      "selected": false
    }
  ]
}
```

---

### Select Proposal

**POST** `/api/v1/sessions/{session_id}/proposals/{proposal_id}/select`

Selects a specific proposal approach.

**Parameters:**
- `session_id` (path): UUID of the session
- `proposal_id` (path): ID of the proposal

**Response:** `200 OK`
```json
{
  "session_id": "uuid-string",
  "selected_proposal": "1",
  "locked_constraints": {
    "selected_approach": "Monolithic Approach"
  }
}
```

---

### Approve Plan

**POST** `/api/v1/sessions/{session_id}/approve`

Approves the plan for execution.

**Response:** `200 OK`
```json
{
  "session_id": "uuid-string",
  "status": "APPROVED",
  "execution_graph": [
    {
      "step_id": 1,
      "task": "Create project structure",
      "status": "PENDING",
      "dependencies": []
    }
  ]
}
```

---

### Execute Plan

**POST** `/api/v1/sessions/{session_id}/execute`

Executes the approved plan.

**Request Body:** (optional)
```json
{
  "context": {
    "additional_data": "value"
  }
}
```

**Response:** `200 OK`
```json
{
  "session_id": "uuid-string",
  "status": "EXECUTING",
  "execution_graph": [
    {
      "step_id": 1,
      "task": "Create project structure",
      "status": "IN_PROGRESS",
      "started_at": "2025-02-28T10:05:00Z"
    }
  ]
}
```

---

### Stream Execution

**GET** `/api/v1/sessions/{session_id}/stream`

Streams execution updates using Server-Sent Events (SSE).

**Response:** `text/event-stream`
```
data: {"type": "step_started", "step_id": 1}

data: {"type": "step_completed", "step_id": 1, "output": "..."}

data: {"type": "execution_completed", "final_output": {...}}
```

---

## External Context

### Add GitHub Context

**POST** `/api/v1/sessions/{session_id}/context/github`

Adds GitHub repository context to the session.

**Request Body:**
```json
{
  "repo_url": "https://github.com/user/repo"
}
```

**Response:** `201 Created`
```json
{
  "id": "context-id",
  "source_type": "github",
  "source_url": "https://github.com/user/repo",
  "content_summary": "Repository: user/repo\nLanguage: TypeScript\n...",
  "metadata": {
    "language": "TypeScript",
    "file_count": 42,
    "dependencies": ["react", "vite"]
  }
}
```

**Notes:**
- Works with public repos without authentication
- Set `GITHUB_TOKEN` for private repos
- Analyzes structure, dependencies, and key files

---

### Add Web Search Context

**POST** `/api/v1/sessions/{session_id}/context/web-search`

Adds web search results to the session.

**Request Body:**
```json
{
  "query": "FastAPI best practices 2025"
}
```

Or omit query for auto-generated query based on intent.

**Response:** `201 Created`
```json
{
  "id": "context-id",
  "source_type": "web_search",
  "content_summary": "Top 10 results for 'FastAPI best practices 2025':\n1. ...",
  "metadata": {
    "query": "FastAPI best practices 2025",
    "result_count": 10,
    "provider": "tavily"
  }
}
```

**Requirements:**
- Set `TAVILY_API_KEY` in environment
- Or configure alternative search provider

---

### Upload File Context

**POST** `/api/v1/sessions/{session_id}/context/upload`

Uploads a file for context extraction.

**Request:** `multipart/form-data`
```
file: <binary file data>
```

**Response:** `201 Created`
```json
{
  "id": "context-id",
  "source_type": "file_upload",
  "content_summary": "Document content extracted...",
  "metadata": {
    "filename": "requirements.pdf",
    "file_type": "application/pdf",
    "size_bytes": 102400
  }
}
```

**Supported Formats:**
- PDF (`.pdf`)
- Text (`.txt`, `.md`)
- Code (`.py`, `.js`, `.ts`, `.json`, `.yaml`)

**Limit:** 10MB default (configurable via `MAX_FILE_SIZE_MB`)

---

### List Contexts

**GET** `/api/v1/sessions/{session_id}/context`

Lists all external contexts for a session.

**Response:** `200 OK`
```json
{
  "contexts": [
    {
      "id": "ctx-1",
      "source_type": "github",
      "created_at": "2025-02-28T10:00:00Z"
    },
    {
      "id": "ctx-2",
      "source_type": "web_search",
      "created_at": "2025-02-28T10:01:00Z"
    }
  ]
}
```

---

## Plan Optimizer

### Optimize Plan

**POST** `/api/v1/optimizer/optimize`

Generates optimized plan variants and multi-model ratings.

**Request Body:**
```json
{
  "selected_proposal_id": "proposal-123",
  "optimization_types": ["simplified", "enhanced"],
  "user_context": "Prefer lower cost over speed"
}
```

**Response:** `200 OK`
```json
{
  "optimization_id": "uuid-string",
  "status": "completed",
  "session_id": "uuid-string",
  "variants": [
    {
      "id": "var-1",
      "proposal_id": "proposal-123",
      "variant_type": "simplified",
      "execution_graph": [...],
      "metadata": {
        "step_count": 3,
        "complexity_score": "Low",
        "estimated_time_minutes": 6,
        "estimated_cost_usd": 0.003
      }
    }
  ],
  "ratings": {
    "var-1": {
      "plan_id": "var-1",
      "ratings": {
        "claude-3.5-sonnet": {
          "model_name": "claude-3.5-sonnet",
          "ratings": {
            "feasibility": 8.5,
            "cost_efficiency": 9.0,
            "time_efficiency": 7.5,
            "complexity": 8.0
          },
          "overall_score": 8.25,
          "reasoning": "..."
        }
      },
      "average_score": 8.25
    }
  }
}
```

---

### Get Optimization Results

**GET** `/api/v1/optimizer/results/{session_id}`

Gets optimization results for a session.

**Response:** `200 OK`
```json
{
  "session_id": "uuid-string",
  "variants": [...],
  "ratings": [...],
  "user_ratings": [...]
}
```

---

### Rate Plans

**POST** `/api/v1/optimizer/rate`

Rates plans using multiple AI models.

**Request Body:**
```json
{
  "plan_ids": ["var-1", "var-2"],
  "models": ["claude-3.5-sonnet", "gpt-4o"],
  "criteria": ["feasibility", "cost_efficiency", "time_efficiency", "complexity"]
}
```

**Response:** `200 OK`
```json
{
  "rating_id": "uuid-string",
  "status": "completed",
  "ratings": {
    "var-1": {
      "plan_id": "var-1",
      "ratings": {
        "gpt-4o": {
          "model_name": "gpt-4o",
          "ratings": {
            "feasibility": 8.0,
            "cost_efficiency": 8.5
          },
          "overall_score": 8.25,
          "reasoning": "..."
        }
      },
      "average_score": 8.25
    }
  }
}
```

---

### Submit User Rating

**POST** `/api/v1/optimizer/user-rating`

Submits user feedback on a plan.

**Request Body:**
```json
{
  "plan_id": "var-1",
  "rating": 5,
  "comment": "Excellent plan, very clear",
  "rationale": "Liked the simplicity"
}
```

**Response:** `200 OK`
```json
{
  "saved": true,
  "rating_id": "rating-id"
}
```

---

### Get Optimizer State

**GET** `/api/v1/optimizer/state/{session_id}`

Gets current optimization state for a session.

**Response:** `200 OK`
```json
{
  "status": "idle",
  "progress": 0.0,
  "message": "Optimization not started"
}
```

---

### Submit Manual Plan

**POST** `/api/v1/optimizer/manual`

Normalizes, evaluates, and ranks a manually supplied plan.

**Request Body:**
```json
{
  "session_id": "uuid-string",
  "title": "Two-phase migration plan",
  "summary": "Move the service to FastAPI with staged rollout",
  "plan_text": "1. Audit current routes\n2. Port handlers\n3. Run shadow traffic",
  "assumptions": ["Current API behavior is documented"],
  "constraints": ["No production downtime"],
  "success_criteria": ["Feature parity", "Passing regression tests"],
  "risks": ["Migration gaps"],
  "fallbacks": ["Rollback to prior release"],
  "steps": [],
  "estimated_time_minutes": 180,
  "estimated_cost_usd": 12.5,
  "metadata": {},
  "judge_models": ["gemini-2.5-flash"]
}
```

---

### Normalize Plan

**POST** `/api/v1/optimizer/normalize`

Converts a raw plan payload into the canonical plan schema.

**Request Body:**
```json
{
  "session_id": "uuid-string",
  "plan": {
    "title": "Candidate plan",
    "steps": ["Inspect current API", "Refactor routes"]
  },
  "source_type": "llm_generated",
  "source_model": "gemini-2.5-flash",
  "planning_style": "baseline",
  "persist": true
}
```

---

### Evaluate Plans

**POST** `/api/v1/optimizer/evaluate`

Evaluates one or more candidate plans with the rubric-based evaluator.

**Request Body:**
```json
{
  "session_id": "uuid-string",
  "plans": [
    {
      "title": "Candidate plan",
      "steps": ["Inspect current API", "Refactor routes"]
    }
  ],
  "judge_models": ["gemini-2.5-flash"]
}
```

---

### Compare Plans

**POST** `/api/v1/optimizer/compare`

Normalizes, evaluates, compares, and ranks multiple candidate plans.

**Request Body:**
```json
{
  "session_id": "uuid-string",
  "plans": [
    {
      "title": "Candidate plan A",
      "steps": ["Inspect current API", "Refactor routes"]
    },
    {
      "title": "Candidate plan B",
      "steps": ["Add compatibility layer", "Migrate incrementally"]
    }
  ],
  "judge_models": ["gemini-2.5-flash"]
}
```

## Utilities

### List Scenarios

**GET** `/api/v1/scenarios`

Lists available scenario templates.

**Response:** `200 OK`
```json
{
  "scenarios": [
    {
      "name": "code_refactoring",
      "description": "Refactor legacy code to modern patterns",
      "input_schema": {...},
      "output_schema": {...}
    }
  ]
}
```

---

### List Models

**GET** `/api/v1/models`

Lists available LLM models.

**Response:** `200 OK`
```json
{
  "models": [
    {
      "name": "gemini-2.5-flash",
      "provider": "google",
      "type": "planner"
    },
    {
      "name": "gemini-3-flash",
      "provider": "google",
      "type": "executor"
    }
  ]
}
```

---

### Health Check

**GET** `/health`

Basic health check endpoint.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid input: field 'user_intent' is required"
}
```

### 404 Not Found
```json
{
  "detail": "Session 'uuid-string' not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "user_intent"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error: LLM API timeout"
}
```

---

## Rate Limiting

Currently, there are no rate limits enforced. Consider implementing for production:

- Recommended: 100 requests/minute per user
- Use `X-RateLimit-*` headers for communication

---

## Pagination

List endpoints support pagination:

**Response Headers:**
```
X-Total-Count: 42
X-Limit: 50
X-Offset: 0
```

**Query Parameters:**
- `limit`: Items per page (default: 50, max: 100)
- `offset`: Items to skip (default: 0)

---

## Authentication

Current version does not require authentication. For production:

1. Add API key authentication
2. Use OAuth2 for user accounts
3. Implement JWT tokens for sessions

Example future header:
```
Authorization: Bearer <token>
```

---

## Versioning

API version is included in URL path: `/api/v1/`

Future versions will be: `/api/v2/`, `/api/v3/`, etc.

Backward compatibility will be maintained for at least one major version.

---

## SDKs and Libraries

Official SDKs:
- Python: `pip install planweaver` (includes API client)
- JavaScript: Coming soon

Community SDKs:
- Check GitHub for community-contributed libraries

---

## WebSocket Support

Coming soon: Real-time execution updates via WebSocket connection.

---

## Interactive Documentation

For live testing and interactive documentation:

1. Start the server: `uv run uvicorn src.planweaver.api.main:app --reload`
2. Open: `http://localhost:8000/docs`
3. Use Swagger UI to test endpoints

---

## Support

For API issues:
- Review [architecture.md](architecture.md)
- Check [../guides/deployment.md](../guides/deployment.md)
- Open an issue on GitHub
