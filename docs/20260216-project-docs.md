# PlanWeaver

Universal LLM Planning & Execution Engine

## Overview

PlanWeaver is a FastAPI-based application that uses Large Language Models to decompose user requests into executable step-by-step plans. It supports multiple LLM providers through LiteLLM and features a planning/execution workflow with scenario templates.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                           │
│  (FastAPI - routes.py, main.py)                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Orchestrator                            │
│  (orchestrator.py - coordinates Planner & Router)          │
└─────────────────────────────────────────────────────────────┘
            │                                           │
            ▼                                           ▼
┌─────────────────────┐                    ┌─────────────────────┐
│      Planner        │                    │   Execution Router  │
│  (planner.py)       │                    │   (router.py)       │
│  - Intent analysis  │                    │  - Step execution   │
│  - Task decompose   │                    │  - Retry logic      │
│  - Proposal gen     │                    │  - Output aggregate │
└─────────────────────┘                    └─────────────────────┘
            │                                           │
            ▼                                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM Gateway                             │
│  (llm_gateway.py - unified interface to LiteLLM)          │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
      DeepSeek          Claude            Gemini 3
```

## Key Components

### API Routes (`src/planweaver/api/routes.py`)
- `POST /api/v1/sessions` - Create new planning session
- `GET /api/v1/sessions/{id}` - Get session state
- `POST /api/v1/sessions/{id}/questions` - Answer clarifying questions
- `POST /api/v1/sessions/{id}/proposals/{id}/select` - Select approach
- `POST /api/v1/sessions/{id}/approve` - Approve execution plan
- `POST /api/v1/sessions/{id}/execute` - Execute plan
- `GET /api/v1/scenarios` - List available scenarios
- `GET /api/v1/models` - List available LLM models

### Planner (`src/planweaver/services/planner.py`)
- Analyzes user intent
- Decomposes requests into dependency-ordered steps
- Generates strawman proposals (alternative approaches)

### Execution Router (`src/planweaver/services/router.py`)
- Executes steps in dependency order
- Handles retries with exponential backoff (3 attempts)
- Aggregates step outputs

### LLM Gateway (`src/planweaver/services/llm_gateway.py`)
- Unified interface to multiple LLM providers
- JSON repair and validation
- Model listing

### Database (`src/planweaver/db/`)
- SQLite with WAL mode for concurrency
- Stores sessions, plans, execution logs

## Supported Models

| Provider | Model ID | Use Case |
|----------|----------|----------|
| DeepSeek | `deepseek/deepseek-chat` | Primary planner |
| Anthropic | `anthropic/claude-3-5-sonnet-20241022` | Primary executor |
| Anthropic | `anthropic/claude-3-opus-20240229` | Complex tasks |
| OpenAI | `openai/gpt-4o` | Alternative executor |
| Ollama | `ollama/llama2` | Local models |
| Google | `gemini/gemini-3-pro-preview` | Gemini 3 Pro |
| Google | `gemini/gemini-3-flash-preview` | Gemini 3 Flash |
| Google | `gemini/gemini-3-pro-image-preview` | Gemini 3 Vision |

## Configuration

Environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `OPENROUTER_API_KEY` | OpenRouter API key (for DeepSeek) | - |
| `GEMINI_API_KEY` | Google Gemini API key | - |
| `OLLAMA_BASE_URL` | Local Ollama endpoint | `http://localhost:11434` |
| `DEFAULT_PLANNER_MODEL` | Default model for planning | `deepseek/deepseek-chat` |
| `DEFAULT_EXECUTOR_MODEL` | Default model for execution | `anthropic/claude-3-5-sonnet-20241022` |
| `DATABASE_URL` | Database connection string | `sqlite:///./planweaver.db` |
| `CORS_ORIGINS` | Comma-separated CORS origins | `http://localhost:3000` |

## Development

### Setup
```bash
uv sync
```

### Run Tests
```bash
uv run pytest tests/ -v
```

### Lint
```bash
uv run ruff check src/
```

### Run API
```bash
uvicorn src.planweaver.api.main:app --reload
```

## Scenarios

YAML templates in `scenarios/`:
- `code_refactoring.yaml` - Code refactoring workflows
- `market_analysis.yaml` - Market competitor analysis
- `blog_generation.yaml` - Blog post generation
- `data_analysis.yaml` - Data analysis workflows
