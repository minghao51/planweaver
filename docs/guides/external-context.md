# External Context Guide

## Overview

PlanWeaver's external context features enable the planner to work with real-world information from GitHub repositories, web search results, and uploaded documents.

## GitHub Repository Analysis

### What It Extracts

- Repository metadata (name, description, language, stars)
- File structure (top 20 files by size)
- Key files (README, package.json, requirements.txt)
- Dependencies (Python pip packages, Node.js packages)

### Usage Example

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

# Continue planning with repo context
```

### API Endpoint

```bash
POST /api/v1/sessions/{session_id}/context/github
Content-Type: application/json

{
  "repo_url": "https://github.com/username/repository"
}
```

### Configuration

Set in `.env`:
```
GITHUB_TOKEN=ghp_xxxxxxxxxxxx  # Optional, for private repos
```

Get a token from: https://github.com/settings/tokens

## Web Search

### Capabilities

- Real-time web search via Tavily API
- AI-summarized search results
- Automatic query generation from user intent

### Configuration

Set in `.env`:
```
TAVILY_API_KEY=tvly-xxxxxxxxxxxx  # Required for web search
SEARCH_PROVIDER=tavily              # Options: tavily, serper, duckduckgo
```

Get an API key from: https://tavily.com

### Usage

```python
# Manual query
search_context = await context_service.add_web_search_context(
    "FastAPI async best practices"
)

# Auto-generated query from intent
plan = orchestrator.start_session("Build a REST API")
search_context = await context_service.add_web_search_context(
    f"best practices: {plan.user_intent}"
)
```

### API Endpoint

```bash
# With custom query
POST /api/v1/sessions/{session_id}/context/web-search
Content-Type: application/json

{
  "query": "FastAPI async best practices 2025"
}

# Auto-generate query from intent
POST /api/v1/sessions/{session_id}/context/web-search
```

## File Uploads

### Supported Formats

- **Documents**: PDF, TXT, MD
- **Code**: PY, JS, TS, JSON, YAML, YML
- **Size limit**: 10MB (configurable via `MAX_FILE_SIZE_MB`)

### Usage

```python
# Upload file
with open("document.pdf", "rb") as f:
    content = f.read()

file_context = await context_service.add_file_context(
    "document.pdf",
    content
)

plan = orchestrator.add_external_context(plan.session_id, file_context)
```

### API Endpoint

```bash
POST /api/v1/sessions/{session_id}/context/upload
Content-Type: multipart/form-data

file: <binary file data>
```

Example with curl:
```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/context/upload \
  -F "file=@document.pdf"
```

### Configuration

Set in `.env`:
```
MAX_FILE_SIZE_MB=10  # Maximum file size in megabytes
```

## Listing Contexts

### API Endpoint

```bash
GET /api/v1/sessions/{session_id}/context
```

Response:
```json
{
  "session_id": "test-123",
  "contexts": [
    {
      "id": "ctx-abc123",
      "source_type": "github",
      "source_url": "https://github.com/user/repo",
      "created_at": "2025-02-18T10:00:00Z",
      "metadata": {
        "repo_name": "repo",
        "language": "Python",
        "stars": 100
      }
    },
    {
      "id": "ctx-def456",
      "source_type": "web_search",
      "source_url": "search:FastAPI best practices",
      "created_at": "2025-02-18T10:05:00Z",
      "metadata": {
        "query": "FastAPI best practices",
        "result_count": 10
      }
    }
  ]
}
```

## Best Practices

1. **Add context early**: Provide context before planning begins for best results
2. **Multiple sources**: Combine GitHub + web search for comprehensive understanding
3. **Specific queries**: Use targeted web search queries for better results
4. **File selection**: Upload relevant documentation rather than entire codebases

## How Context Improves Planning

When external context is available:

- **Better questions**: Planner generates context-aware clarifying questions
- **Accurate steps**: Execution steps reference actual codebase structure
- **Relevant approaches**: Strawman proposals consider existing patterns
- **Dependency awareness**: Steps account for actual project dependencies

## Example Workflow

```python
# 1. Start session with intent
plan = orchestrator.start_session("Add authentication to this API")

# 2. Add GitHub repo context
github_ctx = await context_service.add_github_context(
    "https://github.com/company/my-api"
)
plan = orchestrator.add_external_context(plan.session_id, github_ctx)

# 3. Search for best practices
search_ctx = await context_service.add_web_search_context(
    "FastAPI JWT authentication 2025"
)
plan = orchestrator.add_external_context(plan.session_id, search_ctx)

# 4. Upload security requirements
with open("security-requirements.pdf", "rb") as f:
    file_ctx = await context_service.add_file_context("security-requirements.pdf", f.read())
plan = orchestrator.add_external_context(plan.session_id, file_ctx)

# 5. Get improved questions
print(plan.open_questions)
# Questions now reference actual codebase, best practices, and requirements

# 6. Generate context-aware execution steps
plan = orchestrator.approve_plan(plan)
for step in plan.execution_graph:
    print(step.task)
# Steps now include specific files and patterns from the repo
```

## Troubleshooting

### GitHub API Rate Limits

If you hit rate limits:
- Add a `GITHUB_TOKEN` to `.env` for higher limits
- Use a personal access token from: https://github.com/settings/tokens

### Web Search Not Working

- Verify `TAVILY_API_KEY` is set in `.env`
- Check your Tavily account has available credits
- Ensure the `SEARCH_PROVIDER` is set to `tavily`

### File Upload Fails

- Check file size is under `MAX_FILE_SIZE_MB` limit
- Verify file extension is in allowed types list
- For PDFs, ensure the file is not corrupted

## API Examples

See `tests/test_api_context.py` for comprehensive usage examples.
