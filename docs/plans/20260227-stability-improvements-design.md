# Stability Improvements Design

**Date:** 2026-02-27
**Status:** Approved
**Issues:** CONCERNS.md #1-8 (High + Medium Priority)

## Overview

This design addresses the top 8 issues identified in the codebase concerns document through **7 independent, focused changes** that can each be reviewed, tested, and merged separately.

**Scope:**
- Issues #1-8 from CONCERNS.md (High + Medium priority)
- Target: Public demo deployment
- Principle: Incremental, isolated changes following simplicity

## Changes

### 1. Frontend Error Handling (Toast Notifications)

**Target:** Issue #1 - Empty exception handlers in 5 components

**Implementation:**
- Create toast notification system (`hooks/useToast.ts`, `components/Toast.tsx`)
- Update 5 components to show error toasts on catch
- Auto-dismiss after 5 seconds, stack vertically, color-coded

**Files:**
- Create: `hooks/useToast.ts`, `components/Toast.tsx`, `components/Toast.test.tsx`
- Modify: `ExecutionPanel.tsx`, `ProposalPanel.tsx`, `NewPlanForm.tsx`, `QuestionPanel.tsx`, `HistoryPage.tsx`, `App.tsx`

**Example:**
```typescript
} catch (error) {
  console.error(error);
  toast.error('Failed to select proposal. Please try again.');
}
```

---

### 2. IP-based Rate Limiting

**Target:** Issue #3 - No rate limiting on API endpoints

**Implementation:**
- Install `slowapi` for rate limiting
- Create rate limiter middleware in `api/middleware.py`
- In-memory storage (appropriate for demo)
- Rate limits per IP address

**Limits:**
- Expensive operations (create session, execute): 10/hour
- Read operations (get session, list sessions): 60/minute
- Metadata (scenarios, models): 30/minute
- Exempt localhost from rate limiting

**Files:**
- `pyproject.toml` - Add slowapi dependency
- Create: `src/planweaver/api/middleware.py`
- Modify: `api/main.py`, `api/routers/sessions.py`

**Example:**
```python
@limiter.limit("10/hour")
async def create_session(request: Request, user_intent: str = Body(...)):
    ...
```

---

### 3. Async Blocking Fixes

**Target:** Issue #5 - Blocking `time.sleep()` in async code

**Implementation:**
- Replace `time.sleep()` with `await asyncio.sleep()`
- No API changes - purely internal refactoring
- Same delay values, non-blocking

**Files:**
- `src/planweaver/services/router.py` - Lines 95 and 171-186

**Example:**
```python
# Before: time.sleep(retry_delay)
# After:  await asyncio.sleep(retry_delay)
```

---

### 4. Input Validation

**Target:** Issue #8 - Insufficient input validation

**Implementation:**
- Add validation rules to Pydantic schemas
- Length constraints and format validation
- Return 422 Unprocessable Entity with specific errors

**Validation Rules:**
- `user_intent`: 1-5000 chars
- `scenario_name`: 1-100 chars, alphanumeric + spaces/hyphens/underscores
- `proposal_ids`: List of 1-10 items
- `Answer.answers`: Each answer 1-2000 chars
- File uploads: Max 10MB, verify MIME type

**Files:**
- `src/planweaver/api/schemas.py`
- Add tests in `tests/test_validation.py`

**Example:**
```python
class CreateSessionRequest(BaseModel):
    user_intent: str = Field(min_length=1, max_length=5000)
    scenario_name: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9 _-]+$"
    )
```

---

### 5. API Error Messages

**Target:** Issue #6 - Generic error messages to users

**Implementation:**
- Add specific error messages in exception handlers
- Create consistent error response format
- Log full error server-side, show user-friendly message client-side

**Design:**
- Use HTTPException with descriptive `detail` messages
- Include actionable information when possible
- Don't expose internal implementation details

**Files:**
- `api/routers/sessions.py`
- `services/planner.py`
- `services/comparison_service.py`
- `frontend/src/hooks/useApi.ts`

**Example:**
```python
# Before: raise HTTPException(status_code=500, detail="Unknown error")
# After:  raise HTTPException(status_code=500, detail="Failed to generate proposals. Please try again with a more specific intent.")
```

---

### 6. Server-Sent Events (SSE)

**Target:** Issue #7 - Frontend polling for updates

**Implementation:**
- Add SSE endpoint: `GET /sessions/{id}/stream`
- Create SSE client hook in frontend
- Replace polling in PlanView with SSE connection
- Auto-reconnect with exponential backoff
- Fall back to polling if SSE not supported

**Event Types:**
- `step_started`
- `step_completed`
- `step_failed`
- `execution_complete`

**Files:**
- Create: `api/routers/stream.py`, `hooks/useSSE.ts`
- Modify: `components/PlanView.tsx`, `services/router.py`

**Backend:**
```python
@router.get("/sessions/{session_id}/stream")
async def stream_execution(session_id: str):
    async def event_generator():
        async for event in execution_events:
            yield f"event: {event.type}\ndata: {event.json()}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Frontend:**
```typescript
const useSSE = (url: string) => {
  useEffect(() => {
    const eventSource = new EventSource(url);
    eventSource.onmessage = (e) => setData(JSON.parse(e.data));
    return () => eventSource.close();
  }, [url]);
  return data;
};
```

---

### 7. Backend Exception Handling

**Target:** Issue #4 - Broad/bare exception handlers

**Implementation:**
- Replace bare `except Exception:` with specific types
- Add `logger.exception()` for unexpected errors
- Re-raise unexpected errors instead of hiding them
- Return sensible defaults for expected errors

**Files:**
- `services/planner.py:88`
- `services/comparison_service.py:72`
- `services/context_service.py:49,75,98`
- `api/routers/sessions.py:155`

**Example:**
```python
# Before
try:
    proposals = await self.generate_proposals(intent)
except Exception:
    return []

# After
try:
    proposals = await self.generate_proposals(intent)
except (ValueError, json.JSONDecodeError) as e:
    logger.error(f"Failed to generate proposals: {e}")
    return []
except Exception as e:
    logger.exception(f"Unexpected error generating proposals")
    raise
```

---

## Testing Strategy

Each change will include appropriate tests:

1. **Toast notifications** - Component tests for render/dismiss
2. **Rate limiting** - Integration tests for limits and 429 responses
3. **Async fixes** - Verify non-blocking with concurrent requests
4. **Input validation** - Test valid/invalid inputs, edge cases
5. **Error messages** - Test error scenarios and message formats
6. **SSE** - Test connection, events, reconnection
7. **Exception handling** - Test specific and unexpected errors

## Deployment Considerations

- **Order matters**: Deploy backend changes before frontend (SSE endpoint needed first)
- **Backwards compatible**: All changes maintain existing API contracts
- **Feature flags**: None needed - all changes are additive or improvements
- **Monitoring**: Add metrics for rate limit hits, SSE connections

## Rollback Plan

Each change can be independently reverted:
- Frontend changes: Revert component commits
- Backend changes: Revert service/API commits
- Rate limiting: Disable via config or revert middleware

## Success Criteria

- ✅ All empty catch blocks show user feedback
- ✅ Rate limits prevent abuse (measured via logs)
- ✅ No blocking operations in async code (verified via profiling)
- ✅ All inputs validated before processing
- ✅ Users see actionable error messages
- ✅ Real-time updates via SSE (no polling)
- ✅ Specific exceptions caught, unexpected errors logged and re-raised

## Dependencies

- **slowapi** - Rate limiting (new dependency)
- Existing packages: Framer Motion (animations), FastAPI (SSE support)

## Next Steps

1. Invoke writing-plans skill to create detailed implementation plan
2. Implement changes in order (1-7)
3. Test each change independently
4. Merge incrementally
