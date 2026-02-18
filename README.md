# PlanWeaver

Universal LLM Planning & Execution Engine

## What is PlanWeaver?

PlanWeaver separates LLM reasoning from execution using a two-stage pattern. A planning model (DeepSeek) analyzes intent, asks clarifying questions, and decomposes tasks into a dependency graph. An execution model (Claude) then runs each step in the correct order.

## Features

- **Interactive Planning** - Planner asks clarifying questions before execution
- **Strawman Proposals** - Get multiple approach options to choose from
- **DAG Execution** - Tasks run in dependency order with retry logic
- **Model Agnostic** - Swap planners/executors via LiteLLM (DeepSeek, Claude, GPT-4o, etc.)
- **Scenario Templates** - Define reusable workflows in YAML
- **External Context** - Enhance planning with GitHub repos, web search, and uploaded files

## Quick Start

```bash
# Install
pip install -r requirements.txt
cp .env.example .env  # Add your API keys

# Run the API server
planweaver serve
```

## CLI Usage

```bash
# Start an interactive planning session
planweaver plan "Build a Python CLI to scrape weather data"

# Execute an existing plan
planweaver execute <session_id>
```

## Python API

```python
from planweaver import Orchestrator

orchestrator = Orchestrator(
    planner_model="deepseek/deepseek-chat",
    executor_model="anthropic/claude-3-5-sonnet-20241022"
)

# Start planning
plan = orchestrator.start_session("Build a REST API for inventory management")

# Answer clarifying questions
if plan.open_questions:
    answers = {q.id: "Use FastAPI" for q in plan.open_questions if not q.answered}
    plan = orchestrator.answer_questions(plan, answers)

# Get approach options
proposals = orchestrator.get_strawman_proposals(plan)

# Approve and execute
plan = orchestrator.approve_plan(plan)
result = orchestrator.execute(plan)
print(result.final_output)
```

## External Context Sources

PlanWeaver can enhance planning by incorporating external context:

### GitHub Repositories

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{id}/context/github \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

The planner will analyze the repository structure, dependencies, and key files to generate context-aware questions and steps.

### Web Search

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{id}/context/web-search \
  -H "Content-Type: application/json" \
  -d '{"query": "FastAPI best practices 2025"}'
```

Or let the planner generate the query:
```bash
curl -X POST http://localhost:8000/api/v1/sessions/{id}/context/web-search
```

### File Uploads

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{id}/context/upload \
  -F "file=@document.pdf"
```

Supported formats: PDF, TXT, MD, PY, JS, TS, JSON, YAML

### Python API for External Context

```python
from planweaver import Orchestrator
from planweaver.services.context_service import ContextService

orchestrator = Orchestrator()
context_service = ContextService(config, llm_gateway)

# Start session
plan = orchestrator.start_session("Refactor to TypeScript")

# Add GitHub context
github_context = await context_service.add_github_context(
    "https://github.com/user/react-app"
)
plan = orchestrator.add_external_context(plan.session_id, github_context)

# Add web search context
search_context = await context_service.add_web_search_context(
    "TypeScript migration best practices"
)
plan = orchestrator.add_external_context(plan.session_id, search_context)

# Add file context
with open("requirements.txt", "rb") as f:
    file_context = await context_service.add_file_context("requirements.txt", f.read())
plan = orchestrator.add_external_context(plan.session_id, file_context)
```

See `docs/external-context-guide.md` for detailed documentation.

## Configuration

Set these in `.env`:

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | For Gemini models (recommended - default) |
| `ANTHROPIC_API_KEY` | For Claude executor |
| `OPENAI_API_KEY` | For GPT models |
| `OPENROUTER_API_KEY` | For DeepSeek + other models |

**Default Models:**
- Planner: `gemini-2.5-flash` (price-performance)
- Executor: `gemini-3-flash` (latest balanced)

## Scenarios

Pre-built templates in `scenarios/`:
- `code_refactoring.yaml` - Refactor legacy code
- `blog_generation.yaml` - Generate blog content
- `market_analysis.yaml` - Competitor analysis
- `data_analysis.yaml` - Analyze datasets

See `docs/architecture.md` for system design details.
