# Testing Guide

## Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_llm_gateway.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/planweaver
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── test_api.py          # API endpoint tests
├── test_llm_gateway.py  # LLM Gateway tests (Gemini + LiteLLM)
└── test_planner.py      # Planner service tests
```

## Test Coverage

### API Tests (`test_api.py`)

| Test | Description |
|------|-------------|
| `test_create_session_requires_user_intent` | Validates POST /sessions requires user_intent |
| `test_create_session_returns_session_id` | Creates session and returns session_id |
| `test_get_session_not_found` | Returns 404 for non-existent session |
| `test_list_models_returns_models` | Lists available LLM models |
| `test_list_scenarios_returns_scenarios` | Lists available scenarios |
| `test_sessions_endpoint_requires_user_intent` | Validation test for sessions endpoint |
| `test_execute_requires_approved_plan` | Cannot execute non-approved plans |

### LLM Gateway Tests (`test_llm_gateway.py`)

| Test | Description |
|------|-------------|
| `test_complete_returns_content` | Basic completion via LiteLLM |
| `test_complete_with_json_mode` | JSON mode returns valid JSON |
| `test_get_available_models_returns_list` | Returns list of available models |
| `test_get_available_models_contains_gemini` | Contains Gemini models |
| `test_get_available_models_contains_google_provider` | Contains Google provider models |
| `test_acomplete_returns_content` | Async completion via LiteLLM |
| `test_repair_json_handles_invalid_json` | JSON repair handles malformed input |
| `test_is_gemini_model_with_gemini_prefix` | Detects gemini-* models |
| `test_is_gemini_model_with_models_prefix` | Detects models/* prefix |
| `test_is_gemini_model_with_non_gemini` | Correctly identifies non-Gemini models |
| `test_convert_messages_for_gemini` | Converts messages to Gemini format |
| `test_complete_routes_to_gemini_for_gemini_model` | Routes Gemini models to native SDK |
| `test_complete_fallback_to_litellm_for_non_gemini` | Falls back to LiteLLM for non-Gemini |
| `test_complete_gemini_with_json_mode` | Native Gemini SDK with JSON mode |
| `test_acomplete_routes_to_gemini_for_gemine_model` | Async routes to native Gemini |

### Planner Tests (`test_planner.py`)

| Test | Description |
|------|-------------|
| `test_analyze_intent_returns_analysis` | Intent analysis returns constraints/questions |
| `test_analyze_intent_handles_json_error` | Gracefully handles JSON parse errors |
| `test_create_initial_plan_returns_plan` | Creates plan with BRAINSTORMING status |
| `test_decompose_into_steps_returns_steps` | Decomposes into execution steps |
| `test_decompose_handles_json_error` | Fallback step on JSON error |
| `test_generate_strawman_proposals` | Generates approach proposals |
| `test_generate_strawman_handles_json_error` | Empty list on JSON error |

## Mocking Strategy

- **LLM calls**: Mocked via `unittest.mock.Mock` to avoid actual API calls
- **Database**: Uses SQLite in-memory or mocked
- **API endpoints**: Uses `FastAPI TestClient` with mocked orchestrator

## Environment Variables for Testing

Tests require no external services - all LLM calls are mocked. For integration tests with real APIs:

```bash
GOOGLE_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-claude-key
```

## Current Test Status

- **Total tests**: 29
- **Passing**: 29
- **Failed**: 0
- **Warnings**: 3 (deprecated `datetime.utcnow()` - non-blocking)
