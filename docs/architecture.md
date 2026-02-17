# PlanWeaver Architecture

## System Overview

```
User Intent → Planner (DeepSeek) → Execution Graph → Executor (Claude) → Final Output
                    ↓                              ↓
            Clarifying Questions           Step-by-Step Execution
            Strawman Proposals                (DAG-based)
```

## Core Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `Orchestrator` | `orchestrator.py` | Main coordinator - session lifecycle, plan management |
| `Planner` | `services/planner.py` | Intent analysis, question generation, task decomposition |
| `ExecutionRouter` | `services/router.py` | Execute DAG steps in dependency order with retries |
| `LLMGateway` | `services/llm_gateway.py` | LiteLLM wrapper - unified API for all models |
| `TemplateEngine` | `services/template_engine.py` | Load/render YAML scenario templates |

## Data Flow

### Planning Phase
1. `start_session()` - Creates plan, analyzes intent, generates clarifying questions
2. `answer_questions()` - User provides answers, planner locks constraints
3. `get_strawman_proposals()` - Generate 2-3 approach options
4. `approve_plan()` - User selects approach, plan moves to APPROVED

### Execution Phase
1. Router iterates through execution graph
2. For each step (respecting dependencies):
   - Render prompt from scenario template
   - Call LLM via LLMGateway
   - Store result
3. Aggregate all outputs → `final_output`

## Plan Status Lifecycle

```
BRAINSTORMING → AWAITING_APPROVAL → APPROVED → EXECUTING → COMPLETED
      ↑               ↓                 ↓           ↓
      └───────────────┴───────────────┴───────────┴ FAILED
```

## Execution Step Status

```
PENDING → IN_PROGRESS → COMPLETED
              ↓            ↓
            FAILED ← SKIPPED
```

## Entry Points

| File | Purpose |
|------|---------|
| `src/planweaver/cli.py` | CLI: `plan`, `execute`, `serve` |
| `src/planweaver/api/main.py` | FastAPI application |
| `src/planweaver/main.py` | Package exports |

## Technology Stack

- **Backend**: FastAPI + Pydantic v2
- **Database**: SQLite + SQLAlchemy
- **LLM Gateway**: LiteLLM (model-agnostic)
- **Frontend**: React/Vite (optional)
