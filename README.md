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
