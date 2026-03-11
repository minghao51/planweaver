# Testing Guide

## Test Stack

- Backend and service tests use `pytest` from the repository root.
- Frontend component tests use `vitest` from `/Users/minghao/Desktop/personal/planweaver/frontend`.
- Browser flows use Playwright with mocked API responses so the UI can be validated without a running backend.

## Running Tests

```bash
# Backend: full pytest suite with repository defaults
uv run pytest

# Backend: target a specific file
uv run pytest tests/test_llm_gateway.py

# Frontend unit tests
cd frontend
npm run test:run

# Frontend browser tests
cd frontend
npm run e2e
```

The root `pyproject.toml` configures `pytest` with:

- strict asyncio handling
- strict marker/config validation
- branch coverage for `src/planweaver`
- missing-line coverage output in the terminal

## Backend Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── test_api.py                    # API endpoint tests
├── test_context_service.py        # Context loading and search behavior
├── test_llm_gateway.py            # LLM routing and response normalization
├── test_optimizer_services.py     # Plan optimizer service behavior
├── test_plan_evaluation_pipeline.py
└── test_planner.py                # Planner orchestration logic
```

## Frontend Test Structure

```
frontend/
├── src/**/*.test.tsx     # Vitest component and hook tests
├── e2e/fixtures.ts       # Shared Playwright API mocks
├── e2e/planning-flow.spec.ts
├── e2e/history.spec.ts
└── e2e/workbench.spec.ts
```

The Playwright suite starts Vite locally and intercepts `/api/v1/*` requests. That keeps browser coverage deterministic and focused on UI behavior:

- new plan creation and navigation into plan stages
- history filtering and session discovery
- workbench flows across variants, manual plans, evaluation, and comparison

## Mocking Strategy

- **LLM calls**: Mocked via `unittest.mock.Mock` to avoid actual API calls
- **Database**: Uses the repo test database fixtures from `tests/conftest.py`
- **API endpoints**: Uses `FastAPI TestClient` with mocked orchestrator
- **Frontend network calls**: Mocked in Playwright route handlers and Vitest hook stubs

## Environment Variables for Testing

Tests require no external services - all LLM calls are mocked. For integration tests with real APIs:

```bash
GOOGLE_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-claude-key
```
