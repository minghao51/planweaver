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

- **LLM calls**: Mocked via `unittest.mock.Mock` to avoid actual API calls (except `llm_e2e` tests)
- **Database**: Uses the repo test database fixtures from `tests/conftest.py`
- **API endpoints**: Uses `FastAPI TestClient` with mocked orchestrator
- **Frontend network calls**: Mocked in Playwright route handlers and Vitest hook stubs

## Test Markers

Tests are categorized using pytest markers to enable selective test execution:

| Marker | Purpose | Files | LLM Calls |
|--------|---------|-------|-----------|
| `unit` | Pure unit tests, all mocks | `test_planner.py`, `test_llm_gateway.py`, `test_debate.py`, `test_ensemble.py`, `test_comparison_service.py`, `test_critic.py` | No (mocked) |
| `integration` | Component integration tests | `test_phase1_integration.py`, `test_phase2_integration.py`, `test_e2e_context.py` | No (mocked) |
| `llm_e2e` | End-to-end workflows with real LLM | `test_multiagent_integration.py` | **Yes** |
| `ui_e2e` | UI-only end-to-end (Playwright) | `test_ui_e2e.py` | No |

### Running Tests by Marker

```bash
# Run only unit tests (default)
uv run pytest -m "not llm_e2e and not ui_e2e"

# Run only integration tests
uv run pytest -m integration

# Run only LLM E2E tests (requires API keys)
uv run pytest -m llm_e2e

# Run only UI E2E tests
uv run pytest -m ui_e2e

# Skip tests that make actual LLM calls
uv run pytest -m "not llm_e2e"
```

## Environment Variables for Testing

- **Unit/Integration tests**: Require no external services - all LLM calls are mocked
- **LLM E2E tests** (`llm_e2e`): Require actual API keys (stored in `.env` file, auto-loaded by tests)

The `.env` file is auto-loaded by `tests/conftest.py` before tests run. Ensure your API keys are set:

```bash
GOOGLE_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-claude-key
```

## Coverage Reports

```bash
# Generate HTML coverage report
uv run pytest --cov=src/planweaver --cov-report=html

# Open coverage report in browser
open htmlcov/index.html

# Other coverage formats
uv run pytest --cov=src/planweaver --cov-report=term-missing  # terminal with missing lines
uv run pytest --cov=src/planweaver --cov-report=lcov         # lcov format
```

## HTML Test Reports

Generate HTML test reports with marker breakdown using `pytest-html`:

```bash
# Generate HTML test report (saved to htmlcov/)
uv run pytest --html=htmlcov/test-report.html --self-contained-html

# Open test report in browser
open htmlcov/test-report.html

# Combined: coverage report + test report
uv run pytest --html=htmlcov/test-report.html --self-contained-html --cov=src/planweaver --cov-report=html
open htmlcov/index.html          # coverage
open htmlcov/test-report.html   # test results
```

The HTML report includes:
- Test results grouped by file/marker
- Pass/fail/skip counts
- Execution time per test
- Filterable by marker in the UI
