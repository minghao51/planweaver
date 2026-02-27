# PlanWeaver Architecture

## System Overview

```
User Intent + External Context → Planner → Execution Graph → Executor → Final Output
                     ↓                  ↓                       ↓
              (Optional Sources)  Context-Aware        Step-by-Step
                                    Analysis            Execution
              - GitHub Repos                          (DAG-based)
              - Web Search
              - File Uploads
```

## Core Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `Orchestrator` | `orchestrator.py` | Main coordinator - session lifecycle, plan management, context handling |
| `Planner` | `services/planner.py` | Intent analysis, question generation, task decomposition with context awareness |
| `ExecutionRouter` | `services/router.py` | Execute DAG steps in dependency order with retries |
| `LLMGateway` | `services/llm_gateway.py` | LiteLLM wrapper - unified API for all models |
| `TemplateEngine` | `services/template_engine.py` | Load/render YAML scenario templates |
| `ContextService` | `services/context_service.py` | External context manager for GitHub, web search, file uploads |
| `GitHubAnalyzer` | `services/github_analyzer.py` | Extract repo structure, dependencies, key files |
| `WebSearchService` | `services/web_search_service.py` | Web search with AI-summarized results (Tavily) |
| `FileProcessorService` | `services/file_processor.py` | Parse PDFs, text, and code files for context |
| `VariantGenerator` | `services/variant_generator.py` | **NEW** - Generate AI-optimized plan variants |
| `ModelRater` | `services/model_rater.py` | **NEW** - Rate plans using multiple AI models |
| `OptimizerService` | `services/optimizer_service.py` | **NEW** - Orchestrate optimization workflow |

## Data Flow

### Planning Phase (with External Context)

1. **Session Creation with Context** (optional)
   - User provides GitHub URL, web search query, or uploads file
   - `ContextService` processes external sources:
     - **GitHub**: Extract repo structure, dependencies, key files
     - **Web Search**: Search Tavily API, summarize results
     - **File Upload**: Parse PDF/text/code, extract content
   - Contexts stored as `ExternalContext` objects in Plan

2. **Intent Analysis** (enhanced)
   - `start_session()` - Creates plan with optional contexts
   - `Planner.analyze_intent()` - **Context-aware prompt generation**
   - Planner uses external context to generate better questions:
     - For GitHub: Asks framework-specific questions
     - For Web Search: Incorporates current best practices
     - For Files: References document content

3. **Question & Proposal Cycle**
   - `answer_questions()` - User provides answers, planner locks constraints
   - `get_strawman_proposals()` - Generate 2-3 approach options (context-aware)
   - `approve_plan()` - User selects approach, plan moves to APPROVED

### Execution Phase
1. Router iterates through execution graph
2. For each step (respecting dependencies):
   - Render prompt from scenario template
   - Call LLM via LLMGateway
   - Store result
3. Aggregate all outputs → `final_output`

### External Context Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     External Context Sources                      │
├──────────────────┬──────────────────┬────────────────────────────┤
│   GitHub Repos   │    Web Search    │       File Uploads         │
├──────────────────┼──────────────────┼────────────────────────────┤
│ • Repo metadata  │ • Tavily API     │ • PDF parsing (PyPDF2)      │
│ • File structure │ • AI summary     │ • Text/code extraction      │
│ • Dependencies   │ • Top 10 results │ • Size limits (10MB)        │
│ • Key files      │ • Query result   │ • Type validation          │
└──────────────────┴──────────────────┴────────────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │   ContextService    │
                 │  (Unified Manager)  │
                 └─────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │   ExternalContext   │
                 │   (Data Model)      │
                 └─────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │      Plan           │
                 │  (external_contexts)│
                 └─────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │      Planner        │
                 │  (Context-Aware)    │
                 └─────────────────────┘
```

### Plan Optimizer Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Proposal Selection                           │
└─────────────────────────────────────────────────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │   OptimizerStage    │
                 │   (Frontend)        │
                 └─────────────────────┘
                           ↓
        ┌──────────────────┴──────────────────┐
        ↓                                     ↓
┌─────────────────────┐           ┌─────────────────────┐
│  VariantGenerator   │           │    ModelRater       │
│  (Backend)          │           │    (Backend)        │
├─────────────────────┤           ├─────────────────────┤
│ • Simplified        │           │ • Claude 3.5 Sonnet │
│ • Enhanced          │           │ • GPT-4o            │
│ • Cost-Optimized    │           │ • DeepSeek V3       │
└─────────────────────┘           └─────────────────────┘
        ↓                                     ↓
        └──────────────────┬──────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │  Optimized Variants │
                 │  + Multi-Model      │
                 │  Ratings            │
                 └─────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │  Comparison Panel   │
                 │  (Side-by-Side)     │
                 └─────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │   User Selection    │
                 │   + Feedback        │
                 └─────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │   Execution Phase   │
                 └─────────────────────┘
```

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
| `src/planweaver/api/routes.py` | API endpoints for sessions, scenarios, **context management** |
| `src/planweaver/main.py` | Package exports |

### New API Endpoints (External Context)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions/{id}/context/github` | Add GitHub repository context |
| POST | `/api/v1/sessions/{id}/context/web-search` | Add web search results (auto-query or manual) |
| POST | `/api/v1/sessions/{id}/context/upload` | Upload file for context extraction |
| GET | `/api/v1/sessions/{id}/context` | List all external contexts for session |

### New API Endpoints (Plan Optimizer)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/optimizer/optimize` | Generate optimized variants and rate plans |
| GET | `/api/v1/optimizer/results/{session_id}` | Get optimization results for session |
| POST | `/api/v1/optimizer/rate` | Rate plans with multiple AI models |
| POST | `/api/v1/optimizer/user-rating` | Save user feedback on plans |
| GET | `/api/v1/optimizer/state/{session_id}` | Get current optimization state |

## Technology Stack

- **Backend**: FastAPI + Pydantic v2
- **Database**: SQLite + SQLAlchemy
- **LLM Gateway**: LiteLLM (model-agnostic)
- **Frontend**: React/Vite (optional)

### External Context Dependencies

| Library | Purpose | Version |
|---------|---------|---------|
| `PyGithub` | GitHub API access | >=2.1.1 |
| `tavily-python` | Web search API | >=0.3.0 |
| `PyPDF2` | PDF text extraction | >=3.0.0 |
| `python-multipart` | File upload support | >=0.0.6 |

### Data Models

```python
# Core planning models
Plan
├── session_id: str
├── user_intent: str
├── status: PlanStatus
├── locked_constraints: dict
├── open_questions: list[OpenQuestion]
├── strawman_proposals: list[StrawmanProposal]
├── execution_graph: list[ExecutionStep]
├── external_contexts: list[ExternalContext]  # NEW
└── final_output: dict

# External context model
ExternalContext
├── id: str
├── source_type: "github" | "web_search" | "file_upload"
├── source_url: str | None
├── content_summary: str  # Planner-ready formatted content
├── metadata: dict  # Source-specific data
└── created_at: datetime

# Plan optimizer models
OptimizedVariant
├── id: str
├── session_id: str
├── proposal_id: str
├── variant_type: "simplified" | "enhanced" | "cost-optimized"
├── execution_graph: list[ExecutionStep]
├── variant_metadata: dict
│   ├── step_count: int
│   ├── complexity_score: str
│   ├── optimization_notes: str
│   ├── estimated_time_minutes: int
│   └── estimated_cost_usd: float
└── created_at: datetime

PlanRating
├── id: str
├── session_id: str
├── plan_id: str
├── model_name: str
├── ratings: dict
│   ├── feasibility: float (1-10)
│   ├── cost_efficiency: float (1-10)
│   ├── time_efficiency: float (1-10)
│   ├── complexity: float (1-10)
│   └── risk_level: float (1-10)
├── reasoning: str
└── created_at: datetime

UserRating
├── id: str
├── session_id: str
├── plan_id: str
├── rating: int (1-5)
├── comment: str | None
├── rationale: str | None
└── created_at: datetime
```

## Configuration

### Environment Variables

```bash
# External Context Configuration
GITHUB_TOKEN=              # GitHub PAT for private repos (optional)
TAVILY_API_KEY=           # Web search API key (optional)
SEARCH_PROVIDER=tavily    # Search provider: tavily, serper, duckduckgo
MAX_FILE_SIZE_MB=10       # File upload size limit
```

### Context Source Capabilities

| Source | What It Provides | When to Use |
|--------|-----------------|-------------|
| **GitHub** | Repo structure, dependencies, key files, language | Refactoring, understanding codebases, adding features |
| **Web Search** | Current best practices, documentation, solutions | Learning new tech, finding libraries, staying current |
| **File Upload** | Document content, code samples, specifications | Processing requirements, analyzing docs, custom context |

### Best Practices

1. **Add Context Early**: Provide context before planning for best results
2. **Combine Sources**: Use GitHub + web search for comprehensive understanding
3. **Specific Queries**: Use targeted web search queries for better results
4. **File Selection**: Upload relevant docs rather than entire codebases
5. **Public Repos**: GitHub works without token for public repositories
6. **API Keys Optional**: Features work without keys but with limitations

## Example Workflows

### Refactoring with GitHub Context

```python
# 1. Start session with repo context
context = await context_service.add_github_context(
    "https://github.com/user/react-app"
)
plan = orchestrator.start_session(
    "Refactor to TypeScript",
    external_contexts=[context]
)

# 2. Planner generates TypeScript-aware questions
# 3. Steps mention specific files from the repo
```

### Market Analysis with Web Search

```python
# 1. Create session
plan = orchestrator.start_session("Analyze AI trends in 2025")

# 2. Add current market data
context = await context_service.add_web_search_context(
    "artificial intelligence trends 2025 market analysis"
)
orchestrator.add_external_context(plan.session_id, context)

# 3. Planner uses recent information in analysis
```

### Document Processing

```python
# 1. Upload requirements document
with open("requirements.pdf", "rb") as f:
    context = await context_service.add_file_context(
        "requirements.pdf",
        f.read()
    )

# 2. Plan based on document content
plan = orchestrator.start_session(
    "Implement features from requirements",
    external_contexts=[context]
)
```
