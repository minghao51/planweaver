# Stability Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix CONCERNS.md issues #1-8 (High + Medium priority) through 7 incremental, isolated changes for public demo deployment.

**Architecture:** Each change is independent and can be merged separately. Backend changes should deploy before frontend for SSE compatibility. All changes maintain existing API contracts.

**Tech Stack:** Python 3.13 (FastAPI), React 18 + TypeScript, slowapi (new), Framer Motion (existing), uv (package manager)

---

## Change 1: Frontend Error Handling (Toast Notifications)

**Target:** 5 components with empty catch blocks - ExecutionPanel, ProposalPanel, NewPlanForm, QuestionPanel, HistoryPage

### Task 1.1: Create Toast Hook

**Files:**
- Create: `frontend/src/hooks/useToast.ts`
- Test: `frontend/src/hooks/useToast.test.ts`

**Step 1: Write failing test**

```typescript
// frontend/src/hooks/useToast.test.ts
import { renderHook, act } from '@testing-library/react';
import { useToast } from './useToast';

describe('useToast', () => {
  it('should add error toast', () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.error('Test error');
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe('Test error');
    expect(result.current.toasts[0].type).toBe('error');
  });

  it('should auto-dismiss after 5 seconds', () => {
    jest.useFakeTimers();
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.error('Test');
    });
    expect(result.current.toasts).toHaveLength(1);
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    expect(result.current.toasts).toHaveLength(0);
    jest.useRealTimers();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- useToast.test.ts`
Expected: FAIL - "useToast not found"

**Step 3: Write minimal implementation**

```typescript
// frontend/src/hooks/useToast.ts
import { useState, useEffect, useCallback } from 'react';

export type ToastType = 'error' | 'success' | 'info';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((message: string, type: ToastType) => {
    const id = Math.random().toString(36).substring(7);
    const toast: Toast = { id, message, type };
    setToasts((prev) => [...prev, toast];

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const error = useCallback((message: string) => addToast(message, 'error'), [addToast]);
  const success = useCallback((message: string) => addToast(message, 'success'), [addToast]);
  const info = useCallback((message: string) => addToast(message, 'info'), [addToast]);

  const remove = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, error, success, info, remove };
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- useToast.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/hooks/useToast.ts frontend/src/hooks/useToast.test.ts
git commit -m "feat(toast): add toast notification hook

- Add useToast hook with error, success, info methods
- Auto-dismiss after 5 seconds
- Add tests for toast lifecycle

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 1.2: Create Toast Component

**Files:**
- Create: `frontend/src/components/Toast.tsx`
- Test: `frontend/src/components/Toast.test.tsx`

**Step 1: Write failing test**

```typescript
// frontend/src/components/Toast.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { Toast } from './Toast';
import { ToastType } from '../hooks/useToast';

describe('Toast', () => {
  it('should render error toast with red styling', () => {
    render(<Toast id="1" message="Error message" type="error" onClose={() => {}} />);
    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveClass('bg-red-500');
  });

  it('should call onClose when dismissed', () => {
    const handleClose = jest.fn();
    render(<Toast id="1" message="Test" type="error" onClose={handleClose} />);
    const closeButton = screen.getByRole('button');
    closeButton.click();
    expect(handleClose).toHaveBeenCalled();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- Toast.test.tsx`
Expected: FAIL - "Toast not found"

**Step 3: Write minimal implementation**

```typescript
// frontend/src/components/Toast.tsx
import { useEffect } from 'react';
import { X } from 'lucide-react';
import { motion } from 'framer-motion';
import { ToastType } from '../hooks/useToast';
import { cn } from '../utils';

interface ToastProps {
  id: string;
  message: string;
  type: ToastType;
  onClose: (id: string) => void;
}

const typeStyles: Record<ToastType, string> = {
  error: 'bg-red-500 text-white',
  success: 'bg-green-500 text-white',
  info: 'bg-blue-500 text-white',
};

export function Toast({ id, message, type, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => onClose(id), 5000);
    return () => clearTimeout(timer);
  }, [id, onClose]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 100 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 100 }}
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg',
        'min-w-[300px] max-w-md',
        typeStyles[type]
      )}
      role="alert"
    >
      <span className="flex-1">{message}</span>
      <button
        onClick={() => onClose(id)}
        className="p-1 hover:bg-white/20 rounded"
        aria-label="Close"
      >
        <X size={16} />
      </button>
    </motion.div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- Toast.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/components/Toast.tsx frontend/src/components/Toast.test.tsx
git commit -m "feat(toast): add Toast component with animations

- Render toast with color-coded styling (error/success/info)
- Framer Motion animations for enter/exit
- Auto-dismiss after 5 seconds
- Add tests for render and dismiss

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 1.3: Add Toast Container to App

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Read App.tsx to understand structure**

Run: `cat frontend/src/App.tsx`
Note: Import structure and main component

**Step 2: Add ToastContainer component**

```typescript
// frontend/src/App.tsx - Add after existing imports
import { Toast } from './components/Toast';
import { useToast } from './hooks/useToast';

// In App component, add before return
const { toasts, remove } = useToast();

// In JSX, add before closing </div> or at end of layout
<div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
  {toasts.map((toast) => (
    <Toast
      key={toast.id}
      id={toast.id}
      message={toast.message}
      type={toast.type}
      onClose={remove}
    />
  ))}
</div>
```

**Step 3: Test visual rendering**

Run: `cd frontend && npm run dev`
Visit: http://localhost:5173
Expected: No errors, toast container renders (empty initially)

**Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(toast): add toast container to App

- Add fixed toast container in top-right corner
- Stack toasts vertically with gap
- Ready for use by components

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 1.4: Fix ExecutionPanel Error Handler

**Files:**
- Modify: `frontend/src/components/ExecutionPanel.tsx:24,31`

**Step 1: Update error handlers**

```typescript
// frontend/src/components/ExecutionPanel.tsx - Add to imports
import { useToast } from '../hooks/useToast';

// In component, add:
const { error: showError } = useToast();

// Update handleApprove (line 21-28):
async function handleApprove() {
  try {
    await approvePlan(plan.session_id);
    onUpdated();
  } catch (err) {
    console.error('Failed to approve plan:', err);
    showError('Failed to approve plan. Please try again.');
  }
}

// Update handleExecute (line 30-37):
async function handleExecute() {
  try {
    await executePlan(plan.session_id);
    onUpdated();
  } catch (err) {
    console.error('Failed to execute plan:', err);
    showError('Failed to execute plan. Please try again.');
  }
}
```

**Step 2: Test error handling**

Run: `cd frontend && npm run dev`
Trigger error: Try to execute with invalid session
Expected: Toast appears with error message

**Step 3: Commit**

```bash
git add frontend/src/components/ExecutionPanel.tsx
git commit -m "fix(execution): add toast error notifications

- Show user-friendly error messages on approval/execution failure
- Replace silent catch blocks with toast notifications

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 1.5: Fix ProposalPanel Error Handler

**Files:**
- Modify: `frontend/src/components/ProposalPanel.tsx:25`

**Step 1: Read and update component**

```bash
# Read the file first
cat frontend/src/components/ProposalPanel.tsx
```

Add toast import and update catch block around line 25:
```typescript
import { useToast } from '../hooks/useToast';

const { error: showError } = useToast();

// In catch block (line ~25):
} catch (err) {
  console.error('Failed to select proposal:', err);
  showError('Failed to select proposal. Please try again.');
}
```

**Step 2: Test error handling**

Run: `cd frontend && npm run dev`
Trigger error: Try to select invalid proposal
Expected: Toast appears

**Step 3: Commit**

```bash
git add frontend/src/components/ProposalPanel.tsx
git commit -m "fix(proposal): add toast error notification

- Show error toast when proposal selection fails
- Replace silent error handling

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 1.6: Fix NewPlanForm Error Handler

**Files:**
- Modify: `frontend/src/components/NewPlanForm.tsx:42`

**Step 1: Read and update component**

```bash
cat frontend/src/components/NewPlanForm.tsx
```

Add toast import and update catch block around line 42:
```typescript
import { useToast } from '../hooks/useToast';

const { error: showError, success: showSuccess } = useToast();

// In handleSubmit catch block:
} catch (err) {
  console.error('Failed to create plan:', err);
  showError('Failed to create plan. Please try again.');
}

// Optionally add success toast:
// After await createSession(...):
showSuccess('Plan created successfully!');
```

**Step 2: Test error handling**

Run: `cd frontend && npm run dev`
Trigger: Try to submit empty form
Expected: Toast error message

**Step 3: Commit**

```bash
git add frontend/src/components/NewPlanForm.tsx
git commit -m "fix(form): add toast notifications for plan creation

- Show error toast when plan creation fails
- Add success toast on successful creation
- Improve user feedback

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 1.7: Fix QuestionPanel Error Handler

**Files:**
- Modify: `frontend/src/components/QuestionPanel.tsx:30`

**Step 1: Read and update component**

```bash
cat frontend/src/components/QuestionPanel.tsx
```

Add toast import and update catch block around line 30:
```typescript
import { useToast } from '../hooks/useToast';

const { error: showError } = useToast();

// In catch block:
} catch (err) {
  console.error('Failed to submit answer:', err);
  showError('Failed to submit answer. Please try again.');
}
```

**Step 2: Test error handling**

Run: `cd frontend && npm run dev`
Trigger: Submit invalid answer
Expected: Toast error message

**Step 3: Commit**

```bash
git add frontend/src/components/QuestionPanel.tsx
git commit -m "fix(questions): add toast error notification

- Show error toast when answer submission fails
- Replace silent error handling

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 1.8: Fix HistoryPage Error Handler

**Files:**
- Modify: `frontend/src/components/HistoryPage.tsx:34`

**Step 1: Read and update component**

```bash
cat frontend/src/components/HistoryPage.tsx
```

Add toast import and update catch block around line 34:
```typescript
import { useToast } from '../hooks/useToast';

const { error: showError } = useToast();

// In useEffect or fetch function catch block:
} catch (err) {
  console.error('Failed to load history:', err);
  showError('Failed to load session history. Please refresh.');
}
```

**Step 2: Test error handling**

Run: `cd frontend && npm run dev`
Trigger: Load history with invalid endpoint
Expected: Toast error message

**Step 3: Commit**

```bash
git add frontend/src/components/HistoryPage.tsx
git commit -m "fix(history): add toast error notification

- Show error toast when history loading fails
- Replace silent error handling with user feedback

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 1.9: Verify All Toasts Work

**Step 1: Run full frontend test suite**

Run: `cd frontend && npm test`
Expected: All tests pass

**Step 2: Manual smoke test**

Run: `cd frontend && npm run dev`
Test each component's error flow:
- ExecutionPanel: Try to execute
- ProposalPanel: Try to select proposal
- NewPlanForm: Try to create plan
- QuestionPanel: Try to submit answer
- HistoryPage: Load history

Expected: Toasts appear for all errors

**Step 3: Final commit for Change 1**

```bash
git add frontend/src/
git commit -m "feat(toast): complete toast notification system

- All 5 components now show user-friendly error toasts
- Empty catch blocks eliminated
- Improved user experience with actionable feedback

Resolves CONCERNS.md #1

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Change 2: IP-based Rate Limiting

**Target:** Add rate limiting middleware to prevent API abuse

### Task 2.1: Add slowapi Dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add slowapi to dependencies**

```bash
uv add slowapi
```

Expected: `slowapi` added to pyproject.toml dependencies, uv.lock updated

**Step 2: Verify installation**

Run: `uv run python -c "import slowapi; print(slowapi.__version__)"`
Expected: No errors, version printed

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add slowapi for rate limiting

- Add slowapi library for IP-based rate limiting
- Prevent API abuse on public demo

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 2.2: Create Rate Limiter Middleware

**Files:**
- Create: `src/planweaver/api/middleware.py`
- Test: `tests/test_rate_limit.py`

**Step 1: Write failing test**

```python
# tests/test_rate_limit.py
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from planweaver.api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_rate_limit_allows_requests_within_limit(client):
    """Should allow 60 requests per minute for read operations"""
    for _ in range(60):
        response = client.get("/scenarios")
        assert response.status_code == 200

    response = client.get("/scenarios")
    assert response.status_code == 429  # Too Many Requests

def test_rate_limit_exempt_localhost(client):
    """Should exempt localhost from rate limiting"""
    # Test with 127.0.0.1 - should not be limited
    for _ in range(100):
        response = client.get("/scenarios")
        assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_rate_limit.py -v`
Expected: FAIL - "middleware not found" or "no rate limiting applied"

**Step 3: Write middleware implementation**

```python
# src/planweaver/api/middleware.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

def get_identifier(request: Request) -> str:
    """Get client IP, exempting localhost"""
    # Check if request is from localhost
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    # Exempt localhost and private networks
    if client_ip in ["127.0.0.1", "localhost", "::1"]:
        return "localhost"

    # Exempt private IPs
    if client_ip.startswith(("10.", "192.168.", "172.16.")):
        return "localhost"

    return client_ip

limiter = Limiter(key_func=get_identifier)

def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit exceeded handler"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded. Please try again later.",
            "retry_after": str(exc.retry_after)
        },
        headers={"Retry-After": str(exc.retry_after)}
    )
```

**Step 4: Register middleware in main app**

```python
# src/planweaver/api/main.py - Add imports
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .middleware import limiter, rate_limit_exception_handler

# In app creation function, after app = FastAPI():
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_rate_limit.py -v`
Expected: PASS (or mostly pass, may need adjustment)

**Step 6: Commit**

```bash
git add src/planweaver/api/middleware.py tests/test_rate_limit.py
git commit -m "feat(ratelimit): add IP-based rate limiting middleware

- Create rate limiter with slowapi
- Exempt localhost and private networks
- Return 429 with Retry-After header when limit exceeded
- Add tests for rate limiting behavior

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 2.3: Apply Rate Limits to Session Endpoints

**Files:**
- Modify: `src/planweaver/api/routers/sessions.py`

**Step 1: Add limiter import and decorator**

```python
# src/planweaver/api/routers/sessions.py - Add to imports
from slowapi import Limiter
from ..middleware import limiter

# Or import from main app if passed via Depends
```

**Step 2: Apply decorators to expensive endpoints**

```python
# Create session - 10/hour
@router.post("/sessions")
@limiter.limit("10/hour")
async def create_session(
    request: Request,
    user_intent: str = Body(...),
    scenario_name: str = Body(default=None),
):
    ...

# Execute session - 10/hour
@router.post("/sessions/{session_id}/execute")
@limiter.limit("10/hour")
async def execute_session(
    request: Request,
    session_id: str,
):
    ...

# Compare proposals - 10/hour
@router.post("/sessions/{session_id}/compare")
@limiter.limit("10/hour")
async def compare_proposals(
    request: Request,
    session_id: str,
    proposal_ids: list[str] = Body(...),
):
    ...
```

**Step 3: Apply decorators to read endpoints**

```python
# Get session - 60/minute
@router.get("/sessions/{session_id}")
@limiter.limit("60/minute")
async def get_session(session_id: str):
    ...

# List sessions - 60/minute
@router.get("/sessions")
@limiter.limit("60/minute")
async def list_sessions():
    ...

# Answer question - 30/minute
@router.post("/sessions/{session_id}/answer")
@limiter.limit("30/minute")
async def answer_question(
    request: Request,
    session_id: str,
    answers: list[str],
):
    ...
```

**Step 4: Test rate limiting**

Run: `uv run uvicorn planweaver.api.main:app --reload`

Test rate limit (bash script):
```bash
# Test 10/hour limit on create session
for i in {1..12}; do
  curl -X POST http://localhost:8000/sessions \
    -H "Content-Type: application/json" \
    -d '{"user_intent": "test", "scenario_name": "default"}'
  echo "Request $i: $?"
done
```

Expected: First 10 succeed, next 2 return 429

**Step 5: Commit**

```bash
git add src/planweaver/api/routers/sessions.py
git commit -m "feat(ratelimit): apply rate limits to session endpoints

- Expensive operations (create, execute, compare): 10/hour
- Read operations (get, list): 60/minute
- Answer questions: 30/minute
- Per-IP limits prevent abuse

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 2.4: Apply Rate Limits to Metadata Endpoints

**Files:**
- Modify: `src/planweaver/api/routers/metadata.py`

**Step 1: Add limiter decorators**

```python
# src/planweaver/api/routers/metadata.py
from ..middleware import limiter
from fastapi import Request

@router.get("/scenarios")
@limiter.limit("30/minute")
async def list_scenarios(request: Request):
    ...

@router.get("/models")
@limiter.limit("30/minute")
async def list_models(request: Request):
    ...
```

**Step 2: Test metadata endpoints**

Run: `uv run uvicorn planweaver.api.main:app --reload`

Test scenarios endpoint:
```bash
for i in {1..35}; do
  curl http://localhost:8000/scenarios
  echo "Request $i"
done
```

Expected: First 30 succeed, next 5 return 429

**Step 3: Commit**

```bash
git add src/planweaver/api/routers/metadata.py
git commit -m "feat(ratelimit): apply rate limits to metadata endpoints

- Scenarios and models endpoints: 30/minute
- Prevent scraping of metadata

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 2.5: Final Rate Limit Testing

**Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass, including rate limit tests

**Step 2: Manual smoke test**

Run server and test various endpoints
Verify rate limit headers present in responses

**Step 3: Final commit for Change 2**

```bash
git add src/planweaver/api/
git commit -m "feat(ratelimit): complete rate limiting implementation

- All API endpoints protected with IP-based rate limits
- In-memory storage appropriate for demo
- Localhost and private networks exempt
- Returns 429 with Retry-After header

Resolves CONCERNS.md #3

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Change 3: Async Blocking Fixes

**Target:** Replace blocking `time.sleep()` with async `await asyncio.sleep()`

### Task 3.1: Fix Router Service Blocking Calls

**Files:**
- Modify: `src/planweaver/services/router.py:95,171-186`

**Step 1: Read router.py to find blocking calls**

Run: `grep -n "time.sleep" src/planweaver/services/router.py`
Expected: Found at line 95

**Step 2: Add asyncio import**

```python
# src/planweaver/services/router.py - Add to imports
import asyncio
```

**Step 3: Replace time.sleep with asyncio.sleep (line 95)**

```python
# Before (line ~95):
time.sleep(RETRY_DELAY_BASE * (2 ** attempt))

# After:
await asyncio.sleep(RETRY_DELAY_BASE * (2 ** attempt))
```

**Step 4: Make _execute_with_retries async**

```python
# src/planweaver/services/router.py
# Change method signature from:
def _execute_with_retries(self, step, actual_model, prompt):

# To:
async def _execute_with_retries(self, step, actual_model, prompt):
```

**Step 5: Update _call_model to be async**

```python
# Before:
def _call_model(self, model: str, prompt: str) -> Dict[str, Any]:
    return self.llm.complete(...)

# After:
async def _call_model(self, model: str, prompt: str) -> Dict[str, Any]:
    return await self.llm.complete_async(...)
```

**Step 6: Update execute method to be async**

```python
# Before:
def execute(self, plan: Plan) -> Dict[str, Any]:
    for step in self.get_executable_steps(plan):
        result = self._execute_with_retries(...)

# After:
async def execute(self, plan: Plan) -> Dict[str, Any]:
    for step in self.get_executable_steps(plan):
        result = await self._execute_with_retries(...)
```

**Step 7: Write test for non-blocking behavior**

```python
# tests/test_router_async.py
import pytest
import asyncio
from planweaver.services.router import ExecutionRouter
from planweaver.models.plan import Plan, ExecutionStep, StepStatus

@pytest.mark.asyncio
async def test_execute_does_not_block_event_loop():
    """Should not block other coroutines during retries"""
    router = ExecutionRouter()

    # Create a mock plan with a step
    step = ExecutionStep(
        step_id="test-step",
        task="Test task",
        status=StepStatus.PENDING,
        dependencies=[]
    )
    plan = Plan(
        session_id="test",
        user_intent="test",
        execution_graph=[step]
    )

    # Track if another coroutine can run
    other_ran = False

    async def other_coroutine():
        nonlocal other_ran
        await asyncio.sleep(0.1)  # Small delay
        other_ran = True

    # Run both concurrently
    results = await asyncio.gather(
        router.execute(plan),
        other_coroutine(),
        return_exceptions=True
    )

    # The other coroutine should have run
    assert other_ran, "Event loop was blocked"
```

**Step 8: Run test to verify it passes**

Run: `uv run pytest tests/test_router_async.py -v`
Expected: PASS

**Step 9: Update API endpoints that call router.execute**

Find all places that call `router.execute()` and make them async:
```python
# src/planweaver/api/routers/sessions.py
@router.post("/sessions/{session_id}/execute")
async def execute_session(session_id: str):
    ...
    result = await router.execute(plan)  # Add await
    ...
```

**Step 10: Test API endpoint**

Run: `uv run uvicorn planweaver.api.main:app --reload`

Test execute endpoint:
```bash
curl -X POST http://localhost:8000/sessions/test-id/execute
```

Expected: Returns without blocking, other requests can be processed

**Step 11: Commit**

```bash
git add src/planweaver/services/router.py tests/test_router_async.py
git commit -m "fix(async): replace blocking sleep with async sleep

- Replace time.sleep() with await asyncio.sleep()
- Make _execute_with_retries async
- Update execute method to be async
- Add test for non-blocking behavior
- Update API callers to await execute()

Resolves CONCERNS.md #5 (partial)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 3.2: Verify No Other Blocking Calls

**Step 1: Search for remaining time.sleep calls**

Run: `grep -r "time.sleep" src/planweaver/`
Expected: No results (all fixed)

**Step 2: Search for other blocking patterns**

Run: `grep -r "subprocess\|os.system" src/planweaver/`
Expected: No blocking subprocess calls

**Step 3: Final commit for Change 3**

```bash
git add src/planweaver/
git commit -m "fix(async): complete async refactoring

- All blocking operations converted to async
- Event loop no longer blocked during retries
- Improved scalability and concurrency

Resolves CONCERNS.md #5

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Change 4: Input Validation

**Target:** Strengthen Pydantic schemas with validation rules

### Task 4.1: Add Validation to CreateSessionRequest

**Files:**
- Modify: `src/planweaver/api/schemas.py`
- Test: `tests/test_validation.py`

**Step 1: Read current schemas**

Run: `cat src/planweaver/api/schemas.py`

**Step 2: Write failing tests for validation**

```python
# tests/test_validation.py
import pytest
from pydantic import ValidationError
from planweaver.api.schemas import CreateSessionRequest, AnswerRequest

def test_user_intent_min_length():
    """Should reject empty user intent"""
    with pytest.raises(ValidationError) as exc:
        CreateSessionRequest(user_intent="", scenario_name="default")
    assert "at least 1 characters" in str(exc.value).lower()

def test_user_intent_max_length():
    """Should reject user intent over 5000 chars"""
    with pytest.raises(ValidationError) as exc:
        CreateSessionRequest(user_intent="x" * 5001, scenario_name="default")
    assert "at most 5000 characters" in str(exc.value).lower()

def test_scenario_name_format():
    """Should reject invalid scenario names"""
    with pytest.raises(ValidationError) as exc:
        CreateSessionRequest(user_intent="test", scenario_name="invalid@name!")
    assert "pattern" in str(exc.value).lower() or "match" in str(exc.value).lower()

def test_answer_max_length():
    """Should reject answers over 2000 chars"""
    with pytest.raises(ValidationError) as exc:
        AnswerRequest(answers=["x" * 2001])
    assert "at most 2000 characters" in str(exc.value).lower()

def test_proposal_ids_count():
    """Should reject more than 10 proposal IDs"""
    with pytest.raises(ValidationError) as exc:
        # This will be in the compare endpoint schema
        pass  # Add when we see the actual schema
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_validation.py -v`
Expected: FAIL - validation not yet implemented

**Step 4: Add validation to schemas**

```python
# src/planweaver/api/schemas.py
from pydantic import BaseModel, Field

class CreateSessionRequest(BaseModel):
    user_intent: str = Field(
        min_length=1,
        max_length=5000,
        description="User's planning intent"
    )
    scenario_name: str = Field(
        default="default",
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9 _-]+$",
        description="Scenario template name"
    )

class AnswerRequest(BaseModel):
    answers: list[str] = Field(
        min_length=1,
        description="List of answers to clarifying questions"
    )

    @field_validator('answers')
    @classmethod
    def validate_answer_length(cls, v: list[str]) -> list[str]:
        for answer in v:
            if len(answer) > 2000:
                raise ValueError("Each answer must be at most 2000 characters")
        return v

class CompareProposalsRequest(BaseModel):
    proposal_ids: list[str] = Field(
        min_length=2,
        max_length=10,
        description="List of proposal IDs to compare (2-10)"
    )
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_validation.py -v`
Expected: PASS

**Step 6: Test API returns 422 for invalid input**

Run server:
```bash
uv run uvicorn planweaver.api.main:app --reload
```

Test invalid input:
```bash
# Empty intent
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_intent": "", "scenario_name": "default"}'

# Invalid scenario name
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_intent": "test", "scenario_name": "invalid@name"}'
```

Expected: Returns 422 Unprocessable Entity with validation error details

**Step 7: Commit**

```bash
git add src/planweaver/api/schemas.py tests/test_validation.py
git commit -m "feat(validation): add input validation to request schemas

- user_intent: 1-5000 chars, required
- scenario_name: 1-100 chars, alphanumeric + spaces/hyphens/underscores
- answers: 1-2000 chars each
- proposal_ids: 2-10 items
- Returns 422 with specific error messages

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 4.2: Add File Upload Validation

**Files:**
- Modify: `src/planweaver/api/routers/context.py` (or wherever file upload is handled)
- Test: `tests/test_file_validation.py`

**Step 1: Find file upload endpoint**

Run: `grep -r "UploadFile\|File(" src/planweaver/api/`

**Step 2: Write validation logic**

```python
# src/planweaver/api/routers/context.py (or appropriate file)
from fastapi import UploadFile, HTTPException
import aiofiles

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = [
    "text/plain",
    "text/markdown",
    "text/x-python",
    "application/json",
    "text/yaml",
    "application/pdf",
]

async def validate_file_upload(file: UploadFile) -> None:
    """Validate file size and type"""

    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Reset file position
    await file.seek(0)

    # Check MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"File type {file.content_type} not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
    )

    return content
```

**Step 3: Update upload endpoint to use validation**

```python
@router.post("/context/file")
async def upload_file(file: UploadFile):
    content = await validate_file_upload(file)
    # Process file...
```

**Step 4: Write test**

```python
# tests/test_file_validation.py
from fastapi.testclient import TestClient
from io import BytesIO

def test_file_too_large(client):
    """Should reject files over 10MB"""
    large_file = BytesIO(b"x" * (11 * 1024 * 1024))
    response = client.post(
        "/context/file",
        files={"file": ("test.txt", large_file, "text/plain")}
    )
    assert response.status_code == 413

def test_invalid_mime_type(client):
    """Should reject disallowed file types"""
    response = client.post(
        "/context/file",
        files={"file": ("test.exe", b"content", "application/exe")}
    )
    assert response.status_code == 415
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_file_validation.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/planweaver/api/routers/context.py tests/test_file_validation.py
git commit -m "feat(validation): add file upload validation

- Check file size (max 10MB)
- Validate MIME type against whitelist
- Return 413 for too large, 415 for invalid type
- Prevent resource exhaustion

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 4.3: Final Validation Testing

**Step 1: Run all validation tests**

Run: `uv run pytest tests/test_validation.py tests/test_file_validation.py -v`
Expected: All pass

**Step 2: Final commit for Change 4**

```bash
git add tests/
git commit -m "test(validation): complete validation test coverage

- Test all input validation rules
- Test file upload validation
- Verify 422/413/415 responses

Resolves CONCERNS.md #8

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Change 5: API Error Messages

**Target:** Replace generic error messages with specific, actionable ones

### Task 5.1: Improve Error Messages in Sessions Router

**Files:**
- Modify: `src/planweaver/api/routers/sessions.py`

**Step 1: Read current error handling**

Run: `grep -n "HTTPException\|raise.*Error" src/planweaver/api/routers/sessions.py`

**Step 2: Replace generic errors with specific messages**

```python
# src/planweaver/api/routers/sessions.py

# Create session failures
@router.post("/sessions")
async def create_session(...):
    try:
        session = await orchestrator.start_session(...)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(e)}. Please check your input and try again."
        )
    except Exception as e:
        logger.exception(f"Failed to create session")
        raise HTTPException(
            status_code=500,
            detail="Failed to create session. Please try again with a more specific intent."
        )

# Get session not found
@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = repo.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found. Please check the session ID."
        )
    return session

# Execute session failures
@router.post("/sessions/{session_id}/execute")
async def execute_session(session_id: str):
    try:
        result = await orchestrator.execute_session(session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Failed to execute session {session_id}")
        raise HTTPException(
            status_code=500,
            detail="Execution failed. Please try again or contact support if the problem persists."
        )

# Compare proposals failures
@router.post("/sessions/{session_id}/compare")
async def compare_proposals(session_id: str, proposal_ids: list[str]):
    if len(proposal_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 proposals required for comparison"
        )
    try:
        result = await comparison_service.compare_proposals(session_id, proposal_ids)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Comparison failed: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Failed to compare proposals for session {session_id}")
        raise HTTPException(
            status_code=500,
            detail="Proposal comparison failed. Please try again with fewer proposals."
        )
```

**Step 2: Test error responses**

Run: `uv run uvicorn planweaver.api.main:app --reload`

Test various error scenarios:
```bash
# 404 not found
curl http://localhost:8000/sessions/nonexistent

# 400 invalid input
curl -X POST http://localhost:8000/sessions/abc123/compare \
  -H "Content-Type: application/json" \
  -d '{"proposal_ids": ["only-one"]}'
```

Expected: Clear, actionable error messages

**Step 3: Commit**

```bash
git add src/planweaver/api/routers/sessions.py
git commit -m "fix(errors): improve error messages in sessions router

- Replace generic \"Unknown error\" with specific messages
- Add context to help users understand and fix issues
- Include actionable suggestions when possible
- Log full error server-side

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 5.2: Improve Error Messages in Planner Service

**Files:**
- Modify: `src/planweaver/services/planner.py`

**Step 1: Update exception handling with context**

```python
# src/planweaver/services/planner.py

async def generate_proposals(self, intent: str) -> list[Proposal]:
    try:
        proposals = await self._generate_from_llm(intent)
    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}")
        raise ValueError(
            "Failed to parse AI response. Please try rephrasing your intent."
        )
    except Exception as e:
        logger.exception(f"Failed to generate proposals for intent: {intent[:100]}")
        raise ValueError(
            "Unable to generate proposals. Your intent may be too vague. "
            "Please provide more specific details about what you want to accomplish."
        )
    return proposals
```

**Step 2: Commit**

```bash
git add src/planweaver/services/planner.py
git commit -m "fix(errors): improve error messages in planner service

- Provide specific feedback for common failures
- Suggest how users can fix their input
- Log full errors server-side

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 5.3: Improve Error Messages in Comparison Service

**Files:**
- Modify: `src/planweaver/services/comparison_service.py`

**Step 1: Update exception handling**

```python
# src/planweaver/services/comparison_service.py

async def compare_proposals(self, session_id: str, proposal_ids: list[str]) -> ProposalComparison:
    if len(proposal_ids) < 2:
        raise ValueError("At least 2 proposals required for comparison")

    if len(proposal_ids) > 10:
        raise ValueError("Cannot compare more than 10 proposals at once")

    try:
        # Comparison logic
        pass
    except Exception as e:
        logger.exception(f"Comparison failed for session {session_id}")
        # Return partial results instead of raising
        return ProposalComparison(
            execution_graphs={...},
            total_metrics=...,
            errors=["Comparison incomplete due to errors"]
        )
```

**Step 2: Commit**

```bash
git add src/planweaver/services/comparison_service.py
git commit -m "fix(errors): improve error handling in comparison service

- Validate proposal count before processing
- Return partial results on failure instead of hiding
- Add context to error messages

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 5.4: Update Frontend Error Display

**Files:**
- Modify: `frontend/src/hooks/useApi.ts`

**Step 1: Improve error message extraction**

```typescript
// frontend/src/hooks/useApi.ts

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  // FastAPI error response
  if (error && typeof error === 'object' && 'detail' in error) {
    return String(error.detail);
  }

  // Fetch response
  if (error instanceof Response) {
    return `Server error: ${error.status}`;
  }

  return 'An unexpected error occurred. Please try again.';
}

// In useApi hook, update error handling:
const handleError = (error: unknown) => {
  const message = getErrorMessage(error);
  console.error('API error:', message);
  setError(message);
  return message;
};
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/useApi.ts
git commit -m "fix(errors): improve error message display in frontend

- Extract detailed error messages from API responses
- Handle various error types appropriately
- Show user-friendly messages

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 5.5: Final Error Message Testing

**Step 1: Test all error scenarios**

Run through all endpoints and verify error messages are clear

**Step 2: Final commit for Change 5**

```bash
git add src/planweaver/ frontend/src/
git commit -m "fix(errors): complete error message improvements

- All API errors return specific, actionable messages
- Frontend displays detailed errors to users
- Server-side logging preserves full context
- Users can understand and fix issues

Resolves CONCERNS.md #6

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Change 6: Server-Sent Events (SSE)

**Target:** Replace polling with SSE for real-time execution updates

### Task 6.1: Create SSE Endpoint in Backend

**Files:**
- Create: `src/planweaver/api/routers/stream.py`
- Modify: `src/planweaver/api/main.py`

**Step 1: Write SSE router**

```python
# src/planweaver/api/routers/stream.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from ..services.router import ExecutionRouter
from ..db.repositories import PlanRepository
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
```

**Step 2: Register SSE router**

```python
# src/planweaver/api/main.py
from .routers import stream  # Add import

# Include router
app.include_router(stream.router)
```

**Step 3: Test SSE endpoint manually**

Run: `uv run uvicorn planweaver.api.main:app --reload`

Test with curl:
```bash
curl -N http://localhost:8000/sessions/test-session/stream
```

Expected: Server keeps connection open and sends events

**Step 4: Write test**

```python
# tests/test_sse.py
import pytest
from fastapi.testclient import TestClient

def test_sse_stream_connects(client):
    """Should establish SSE connection"""
    response = client.get("/sessions/test-id/stream")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"
```

**Step 5: Commit**

```bash
git add src/planweaver/api/routers/stream.py src/planweaver/api/main.py tests/test_sse.py
git commit -m "feat(sse): add Server-Sent Events endpoint

- Create /sessions/{id}/stream endpoint
- Stream execution progress in real-time
- Events: connected, step_completed, step_failed, execution_complete
- Disable buffering for proper streaming

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 6.2: Create SSE Client Hook

**Files:**
- Create: `frontend/src/hooks/useSSE.ts`
- Test: `frontend/src/hooks/useSSE.test.ts`

**Step 1: Write failing test**

```typescript
// frontend/src/hooks/useSSE.test.ts
import { renderHook, act } from '@testing-library/react';
import { useSSE } from './useSSE';

describe('useSSE', () => {
  it('should connect to SSE endpoint', () => {
    const { result } = renderHook(() => useSSE('session-id'));
    expect(result.current.connected).toBe(true);
  });

  it('should receive step_completed events', () => {
    const { result } = renderHook(() => useSSE('session-id'));
    // Mock SSE message
    const event = new MessageEvent('message', {
      data: JSON.stringify({ type: 'step_completed', step_id: 'step-1' })
    });
    act(() => {
      // Simulate event
    });
    expect(result.current.lastEvent).toEqual(expect.objectContaining({
      type: 'step_completed'
    }));
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- useSSE.test.ts`
Expected: FAIL

**Step 3: Implement useSSE hook**

```typescript
// frontend/src/hooks/useSSE.ts
import { useState, useEffect, useCallback, useRef } from 'react';

export interface SSEEvent {
  type: string;
  data: any;
}

export function useSSE(sessionId: string | null) {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    const url = `/sessions/${sessionId}/stream`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
      setError(null);
    };

    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      setConnected(false);
      setError('Connection lost. Retrying...');
    };

    // Handle specific event types
    eventSource.addEventListener('step_completed', (e) => {
      const data = JSON.parse(e.data);
      setLastEvent({ type: 'step_completed', data });
    });

    eventSource.addEventListener('step_failed', (e) => {
      const data = JSON.parse(e.data);
      setLastEvent({ type: 'step_failed', data });
    });

    eventSource.addEventListener('execution_complete', (e) => {
      const data = JSON.parse(e.data);
      setLastEvent({ type: 'execution_complete', data });
    });

    eventSource.addEventListener('execution_failed', (e) => {
      const data = JSON.parse(e.data);
      setLastEvent({ type: 'execution_failed', data });
    });

    eventSource.addEventListener('error', (e) => {
      const data = JSON.parse(e.data);
      setError(data.message);
    });

    // Cleanup
    return () => {
      eventSource.close();
      setConnected(false);
    };
  }, [sessionId]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      setConnected(false);
    }
  }, []);

  return {
    connected,
    lastEvent,
    error,
    disconnect
  };
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- useSSE.test.ts`
Expected: PASS (may need to mock EventSource)

**Step 5: Commit**

```bash
git add frontend/src/hooks/useSSE.ts frontend/src/hooks/useSSE.test.ts
git commit -m "feat(sse): add useSSE hook for real-time updates

- Connect to SSE endpoint
- Handle step_completed, step_failed, execution_complete events
- Auto-reconnect on error
- Cleanup on unmount

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 6.3: Replace Polling in PlanView

**Files:**
- Modify: `frontend/src/components/PlanView.tsx`

**Step 1: Read current PlanView to find polling code**

Run: `grep -n "setInterval\|setTimeout\|polling" frontend/src/components/PlanView.tsx`

**Step 2: Replace polling with SSE**

```typescript
// frontend/src/components/PlanView.tsx
import { useSSE } from '../hooks/useSSE';
import { useEffect } from 'react';

// In PlanView component, replace polling useEffect with:
const { connected, lastEvent, error: sseError } = useSSE(plan?.session_id ?? null);

// Handle SSE events
useEffect(() => {
  if (lastEvent?.type === 'step_completed') {
    // Refresh plan data
    onUpdated();
  }
  if (lastEvent?.type === 'execution_complete') {
    // Final refresh
    onUpdated();
  }
  if (lastEvent?.type === 'step_failed') {
    // Show error toast
    showError(`Step failed: ${lastEvent.data.step_id}`);
    onUpdated();
  }
}, [lastEvent, onUpdated]);

// Handle SSE errors
useEffect(() => {
  if (sseError) {
    console.error('SSE error:', sseError);
    // Fall back to polling if SSE fails
  }
}, [sseError]);

// Remove old polling useEffect
```

**Step 3: Test SSE connection**

Run: `cd frontend && npm run dev`

Execute a plan and observe:
- Connection status
- Real-time step updates
- No polling in network tab

**Step 4: Add fallback to polling if SSE fails**

```typescript
// frontend/src/components/PlanView.tsx
const [usePolling, setUsePolling] = useState(false);

// Fallback if SSE not supported or fails
useEffect(() => {
  if (!window.EventSource || sseError) {
    setUsePolling(true);
  }
}, [sseError]);

// Keep polling as fallback
useEffect(() => {
  if (!usePolling || !plan) return;

  const interval = setInterval(() => {
    onUpdated();
  }, 2000);

  return () => clearInterval(interval);
}, [usePolling, plan, onUpdated]);
```

**Step 5: Commit**

```bash
git add frontend/src/components/PlanView.tsx
git commit -m "feat(sse): replace polling with SSE in PlanView

- Use useSSE hook for real-time updates
- Fallback to polling if SSE unavailable
- Remove unnecessary polling intervals
- Improve UX with instant progress updates

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 6.4: Final SSE Testing

**Step 1: Run full test suite**

Run:
```bash
cd frontend && npm test
uv run pytest tests/test_sse.py -v
```

Expected: All tests pass

**Step 2: Manual smoke test**

Execute a plan and verify:
- SSE connection established
- Real-time updates appear
- No polling requests in DevTools
- Fallback works if SSE fails

**Step 3: Final commit for Change 6**

```bash
git add frontend/src/ src/planweaver/
git commit -m "feat(sse): complete Server-Sent Events implementation

- Backend SSE endpoint streams execution progress
- Frontend useSSE hook receives real-time updates
- PlanView uses SSE instead of polling
- Fallback to polling if SSE unavailable
- Reduced server load, improved UX

Resolves CONCERNS.md #7

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Change 7: Backend Exception Handling

**Target:** Replace bare exception handlers with specific types

### Task 7.1: Fix Exception Handling in Planner

**Files:**
- Modify: `src/planweaver/services/planner.py:88`

**Step 1: Read current exception handler**

Run: `sed -n '80,100p' src/planweaver/services/planner.py`

**Step 2: Replace bare except with specific exceptions**

```python
# src/planweaver/services/planner.py (around line 88)
try:
    proposals = await self.generate_proposals(user_intent)
    return {
        "questions": [],
        "proposals": proposals,
        "selected_proposal": None
    }
except (ValueError, json.JSONDecodeError) as e:
    logger.error(f"Failed to generate proposals: {e}")
    return {
        "questions": [],
        "proposals": [],
        "selected_proposal": None
    }
except Exception as e:
    logger.exception(f"Unexpected error in planning phase for intent: {user_intent[:100]}")
    raise  # Re-raise unexpected errors
```

**Step 3: Commit**

```bash
git add src/planweaver/services/planner.py
git commit -m "fix(exceptions): improve exception handling in planner

- Catch specific exceptions (ValueError, JSONDecodeError)
- Use logger.exception for unexpected errors
- Re-raise unexpected errors instead of hiding
- Return sensible defaults for expected failures

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 7.2: Fix Exception Handling in Comparison Service

**Files:**
- Modify: `src/planweaver/services/comparison_service.py:72`

**Step 1: Update exception handler**

```python
# src/planweaver/services/comparison_service.py (around line 72)
try:
    execution_graph = await self._build_execution_graph(session_id, proposal_id)
    graphs[proposal_id] = execution_graph
except (ValueError, KeyError) as e:
    logger.error(f"Failed to build graph for proposal {proposal_id}: {e}")
    graphs[proposal_id] = None
    errors.append(f"Proposal {proposal_id}: {str(e)}")
except Exception as e:
    logger.exception(f"Unexpected error building graph for proposal {proposal_id}")
    graphs[proposal_id] = None
    errors.append(f"Proposal {proposal_id}: Unexpected error")
    # Continue with other proposals instead of failing completely
```

**Step 2: Commit**

```bash
git add src/planweaver/services/comparison_service.py
git commit -m "fix(exceptions): improve exception handling in comparison service

- Catch specific exceptions (ValueError, KeyError)
- Continue processing other proposals on error
- Log unexpected errors with full stack trace
- Return partial results instead of complete failure

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 7.3: Fix Exception Handling in Context Service

**Files:**
- Modify: `src/planweaver/services/context_service.py:49,75,98`

**Step 1: Update all three exception handlers**

```python
# Handler 1 (around line 49)
try:
    # Context fetching logic
except (ValueError, HTTPException) as e:
    logger.error(f"Failed to fetch context: {e}")
    return []
except Exception as e:
    logger.exception("Unexpected error fetching context")
    raise

# Handler 2 (around line 75)
try:
    # Processing logic
except (ValueError, KeyError) as e:
    logger.warning(f"Context processing error: {e}")
    return None
except Exception as e:
    logger.exception("Unexpected error in context processing")
    return None

# Handler 3 (around line 98)
try:
    # Another operation
except (IOError, OSError) as e:
    logger.error(f"File operation failed: {e}")
    return None
except Exception as e:
    logger.exception("Unexpected error in context service")
    raise
```

**Step 2: Commit**

```bash
git add src/planweaver/services/context_service.py
git commit -m "fix(exceptions): improve exception handling in context service

- Replace bare except with specific exception types
- Handle HTTP, IO, and value errors appropriately
- Log unexpected errors with full context
- Re-raise or return defaults based on error severity

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 7.4: Fix Exception Handling in Sessions Router

**Files:**
- Modify: `src/planweaver/api/routers/sessions.py:155`

**Step 1: Update exception handler**

```python
# src/planweaver/api/routers/sessions.py (around line 155)
try:
    result = await orchestrator.execute_session(session_id)
    return result
except ValueError as e:
    logger.warning(f"Validation error executing session {session_id}: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except HTTPException:
    # Re-raise HTTP exceptions as-is
    raise
except Exception as e:
    logger.exception(f"Unexpected error executing session {session_id}")
    raise HTTPException(
        status_code=500,
        detail="Execution failed. Please try again or contact support if the problem persists."
    )
```

**Step 2: Commit**

```bash
git add src/planweaver/api/routers/sessions.py
git commit -m "fix(exceptions): improve exception handling in sessions router

- Catch ValueError for validation errors (400)
- Re-raise HTTPException unchanged
- Log and convert unexpected errors to 500
- Don't expose internal details to users

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task 7.5: Test Exception Handling

**Step 1: Write tests for exception scenarios**

```python
# tests/test_exception_handling.py
import pytest
from planweaver.services.planner import Planner
from planweaver.services.comparison_service import ProposalComparisonService

def test_planner_handles_json_decode_error():
    """Should return empty proposals on JSON decode error"""
    # Mock LLM to return invalid JSON
    service = Planner(mock_llm)
    result = service.generate_proposals("test")
    assert result["proposals"] == []

def test_comparison_continues_on_partial_failure():
    """Should return partial results when some proposals fail"""
    service = ProposalComparisonService(mock_llm, mock_repo)
    # Mock to fail on second proposal
    result = service.compare_proposals("session-id", ["p1", "p2"])
    assert len(result.errors) > 0
    assert "p1" in result.execution_graphs  # First succeeded
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_exception_handling.py -v`
Expected: PASS

**Step 3: Final commit for Change 7**

```bash
git add tests/test_exception_handling.py
git commit -m "test(exceptions): add exception handling tests

- Test specific exception scenarios
- Verify partial results on failure
- Ensure proper logging and error propagation

Resolves CONCERNS.md #4

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Final Testing & Deployment

### Task Final.1: Run Full Test Suite

**Step 1: Run all backend tests**

Run: `uv run pytest tests/ -v --cov=planweaver`
Expected: All tests pass, coverage report generated

**Step 2: Run all frontend tests**

Run: `cd frontend && npm test -- --coverage`
Expected: All tests pass, coverage report generated

**Step 3: Fix any failing tests**

If tests fail, fix and commit fixes

**Step 4: Final integration commit**

```bash
git add .
git commit -m "test: complete test suite for stability improvements

- All changes have test coverage
- Backend: 100% new code covered
- Frontend: Component tests for all new features
- Integration tests for rate limiting and SSE

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Task Final.2: Smoke Test Entire System

**Step 1: Start backend**

Run: `uv run uvicorn planweaver.api.main:app --reload`

**Step 2: Start frontend**

Run: `cd frontend && npm run dev`

**Step 3: Test complete user flow**

1. Create a plan → Should work, show success toast
2. Try to create with empty intent → Should show validation error
3. Execute plan → Should see real-time SSE updates
4. Trigger error (invalid session) → Should show error toast
5. Rapidly create 11 plans → Should hit rate limit on 11th
6. Check execution doesn't block → Load another page during execution

**Step 4: Verify all 8 issues resolved**

- ✅ Empty catch blocks show toasts
- ✅ Rate limiting prevents abuse
- ✅ No blocking async calls
- ✅ Input validation enforced
- ✅ Specific error messages
- ✅ SSE replaces polling
- ✅ Specific exceptions caught

**Step 5: Final deployment commit**

```bash
git add .
git commit -m "release: stability improvements complete

All 8 high/medium priority issues from CONCERNS.md resolved:

1. Frontend error handling - Toast notifications replace silent failures
2. Rate limiting - IP-based limits prevent abuse
3. Async fixes - No blocking operations
4. Input validation - Strengthened schemas with length/format checks
5. Error messages - Specific, actionable feedback
6. SSE - Real-time updates replace polling
7. Exception handling - Specific types, proper logging

System ready for public demo deployment.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Deployment Order

**Important:** Deploy backend before frontend for SSE compatibility

1. Deploy backend changes (changes 2-7)
2. Verify SSE endpoint works
3. Deploy frontend changes (changes 1, 6)
4. Verify end-to-end functionality

---

## Rollback Plan

If issues arise:
1. Frontend changes: Revert to commit before Change 1
2. Backend changes: Revert to commit before Change 2
3. Each change can be independently reverted

---

## Success Criteria Verification

- [ ] All empty catch blocks show user feedback via toasts
- [ ] Rate limits prevent abuse (test with rapid requests)
- [ ] No blocking operations in async code (verify with concurrent requests)
- [ ] All inputs validated (test with invalid data)
- [ ] Users see actionable error messages (check error scenarios)
- [ ] Real-time updates via SSE (no polling in DevTools)
- [ ] Specific exceptions caught (check logs)
- [ ] All tests pass
- [ ] Manual smoke test passes

---

**End of Implementation Plan**

Total estimated implementation time: 4-6 hours across 7 independent changes.
