# PlanWeaver Architecture Documentation

## Overview

PlanWeaver is a meta-orchestration framework that separates **reasoning** (planning) from **execution**. It uses cost-effective reasoning models to decompose complex requests into structured plans, then routes specific tasks to specialized execution models for high-quality output.

## Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PlanWeaver Engine                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   Planner    │───▶│   Orchestrator│───▶│    Router    │    │
│  │  (DeepSeek) │    │    (Core)    │    │  (Claude)   │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │  Template    │    │   Database   │    │   LLM        │    │
│  │   Engine     │    │   (SQLite)   │    │   Gateway    │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Planner (`services/planner.py`)

**Purpose:** Analyzes user intent and decomposes it into executable steps.

**Key Methods:**
- `analyze_intent()` - Identifies constraints, missing info, complexity
- `decompose_into_steps()` - Generates DAG of execution steps
- `generate_strawman_proposals()` - Creates multiple approach options
- `create_initial_plan()` - Creates Plan object with initial state

**Model:** Uses DeepSeek-V3 (cost-effective reasoning)

### 2. Execution Router (`services/router.py`)

**Purpose:** Executes steps in dependency order with validation.

**Key Methods:**
- `get_executable_steps()` - Returns steps whose deps are satisfied
- `execute_step()` - Runs a single step with LLM
- `execute_plan()` - Runs all steps to completion
- `_get_previous_outputs()` - Aggregates step outputs for context

**Model:** Uses Claude 3.5 Sonnet (high-quality execution)

### 3. Template Engine (`services/template_engine.py`)

**Purpose:** Manages scenario templates and variable substitution.

**Features:**
- YAML-based scenario definitions
- Jinja2-style templating
- Input/output schema validation
- Multi-scenario support

### 4. LLM Gateway (`services/llm_gateway.py`)

**Purpose:** Unified interface to multiple LLM providers.

**Supported Providers:**
- Anthropic (Claude)
- OpenAI (GPT-4o)
- OpenRouter (DeepSeek, etc.)
- Ollama (local models)

**Features:**
- JSON mode with repair (json-repair library)
- Streaming responses
- Token usage tracking

### 5. Database (`db/`)

**Technology:** SQLite with SQLAlchemy

**Tables:**
- `sessions` - Main session/plan storage
- `plans` - Execution plan details
- `execution_logs` - Audit trail

**State Flow:**
```
BRAINSTORMING → AWAITING_APPROVAL → APPROVED → EXECUTING → COMPLETED
                    ↓                                    ↓
              (answer questions)                  (or FAILED)
```

## Data Models

### Plan (`models/plan.py`)

```python
class Plan:
    session_id: str           # Unique session identifier
    status: PlanStatus        # Current state
    user_intent: str          # Original request
    locked_constraints: dict  # Confirmed requirements
    open_questions: list     # Clarifying questions
    strawman_proposals: list # Approach options
    execution_graph: list   # DAG of steps
    final_output: any        # Aggregated results
```

### Scenario (`models/scenario.py`)

```python
class Scenario:
    name: str                    # Display name
    description: str             # What it does
    planner_prompt_template: str  # Planner instructions
    executor_template: str       # Execution instructions
    input_schema: InputSchema     # Required inputs
    output_schema: OutputSchema  # Expected outputs
```

## API Endpoints

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions` | Create new planning session |
| GET | `/api/v1/sessions/{id}` | Get session details |
| POST | `/api/v1/sessions/{id}/questions` | Answer clarifying questions |
| GET | `/api/v1/sessions/{id}/proposals` | Get approach proposals |
| POST | `/api/v1/sessions/{id}/proposals/{pid}/select` | Select approach |
| POST | `/api/v1/sessions/{id}/approve` | Approve plan |
| POST | `/api/v1/sessions/{id}/execute` | Execute plan |

### Utilities

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/scenarios` | List available scenarios |
| GET | `/api/v1/models` | List available models |

## Scenario Library (`scenarios/`)

YAML files defining reusable workflows:

1. **code_refactoring.yaml** - Code modernization
2. **market_analysis.yaml** - Competitor research
3. **blog_generation.yaml** - Content creation
4. **data_analysis.yaml** - Statistical analysis

## Frontend (`frontend/`)

React + TypeScript application with:

- **NewPlanForm** - Request input
- **QuestionPanel** - Clarifying questions
- **ProposalPanel** - Approach selection
- **ExecutionPanel** - Step visualization
- **PlanView** - Main dashboard

## Configuration

Environment variables in `.env`:

```env
ANTHROPIC_API_KEY=          # For Claude
OPENROUTER_API_KEY=         # For DeepSeek
DEFAULT_PLANNER_MODEL=deepseek/deepseek-chat
DEFAULT_EXECUTOR_MODEL=anthropic/claude-3-5-sonnet-20241022
DATABASE_URL=sqlite:///./planweaver.db
```

## Execution Flow

1. **User submits intent** → Planner analyzes request
2. **If incomplete** → User answers clarifying questions
3. **Generate proposals** → User selects approach
4. **Create execution DAG** → User approves plan
5. **Execute steps** → Router runs steps in dependency order
6. **Aggregate outputs** → Final result stored

## Extensibility

- **Add new scenarios:** Create YAML file in `scenarios/`
- **Add new providers:** Extend `LLMGateway` class
- **Customize routing:** Modify `ExecutionRouter` logic
