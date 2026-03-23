# PlanWeaver

Universal LLM Planning and execution engine.

## Overview

PlanWeaver separates planning from execution. A planning model decomposes the request into a structured graph, then execution models run the approved steps with retries, routing, and optional external context.

## Features

- Interactive planning with clarifying questions
- Strawman proposals before execution
- DAG-based execution with retries
- External context from GitHub, web search, and file uploads
- Manual plan normalization, evaluation, and comparison

## Quick Start

```bash
uv sync
cp .env.example .env

# API server
uv run uvicorn src.planweaver.api.main:app --reload

# Optional CLI workflow
uv run python -m src.planweaver.cli plan "Build a Python CLI to scrape weather data"
```

The API is available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

## Configuration

Set these in `.env` as needed:

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Gemini models |
| `ANTHROPIC_API_KEY` | Claude models |
| `OPENAI_API_KEY` | GPT models |
| `OPENROUTER_API_KEY` | DeepSeek and other OpenRouter models |
| `GITHUB_TOKEN` | Private GitHub repository access |
| `TAVILY_API_KEY` | Web search |

Defaults in [`src/planweaver/config.py`](/Users/minghao/Desktop/personal/planweaver/src/planweaver/config.py) use `gemini-2.5-flash` for planning and `gemini-3-flash` for execution.

## Project Layout

- [`src/planweaver`](/Users/minghao/Desktop/personal/planweaver/src/planweaver) contains the backend package
- [`scenarios`](/Users/minghao/Desktop/personal/planweaver/scenarios) contains reusable YAML workflows
- [`docs/README.md`](/Users/minghao/Desktop/personal/planweaver/docs/README.md) is the documentation entry point
- [`scripts/README.md`](/Users/minghao/Desktop/personal/planweaver/scripts/README.md) documents maintenance scripts

## Documentation

- Architecture: [`docs/reference/architecture.md`](/Users/minghao/Desktop/personal/planweaver/docs/reference/architecture.md)
- API reference: [`docs/reference/api.md`](/Users/minghao/Desktop/personal/planweaver/docs/reference/api.md)
- Testing: [`docs/reference/testing.md`](/Users/minghao/Desktop/personal/planweaver/docs/reference/testing.md)
- Deployment: [`docs/guides/deployment.md`](/Users/minghao/Desktop/personal/planweaver/docs/guides/deployment.md)
- External context: [`docs/guides/external-context.md`](/Users/minghao/Desktop/personal/planweaver/docs/guides/external-context.md)
- Optimizer: [`docs/guides/optimizer.md`](/Users/minghao/Desktop/personal/planweaver/docs/guides/optimizer.md)

Historical notes and implementation plans live under [`docs/archive`](/Users/minghao/Desktop/personal/planweaver/docs/archive).
