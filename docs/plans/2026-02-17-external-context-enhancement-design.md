# External Context Enhancement Design

**Date:** 2026-02-17
**Status:** Approved
**Author:** PlanWeaver Team

## Overview

Enhance PlanWeaver's planning capabilities by enabling the integration of external context sources: GitHub repositories, web search results, and uploaded files. This enhancement will allow the planner to generate more informed, context-aware questions and execution steps.

## Goals

- Enable planning with external context from three sources: GitHub repos, web search, and file uploads
- Maintain simplicity - minimal changes to existing codebase
- Support both user-provided and planner-requested context (flexible approach)
- Provide moderate analysis depth - structured context extraction without over-engineering

## Architecture

### Approach: Unified Context Service

Single context service managing all three sources with simple integration points.

### Core Components

#### 1. Context Service
**Location:** `src/planweaver/services/context_service.py`

Methods:
- `add_github_context(repo_url: str) -> ExternalContext`
- `add_web_search_context(query: str) -> ExternalContext`
- `add_file_context(filename: str, content: bytes) -> ExternalContext`

#### 2. ExternalContext Model
**Location:** `src/planweaver/models/plan.py` (extension)

```python
class ExternalContext(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: Literal["github", "web_search", "file_upload"]
    source_url: Optional[str] = None
    content_summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Plan(BaseModel):
    # ... existing fields ...
    external_contexts: List[ExternalContext] = Field(default_factory=list)
```

#### 3. API Endpoints
**Location:** `src/planweaver/api/routes.py` (extensions)

- `POST /api/v1/sessions/{id}/context/github` - Add GitHub repo context
- `POST /api/v1/sessions/{id}/context/web-search` - Add web search results
- `POST /api/v1/sessions/{id}/context/upload` - Upload file for context

#### 4. Planner Integration
**Location:** `src/planweaver/services/planner.py` (modification)

Enhanced `_build_planner_prompt()` method to include external contexts.

## Context Source Implementations

### GitHub Repository Analysis

**Service:** `GitHubContextAnalyzer`

**Extraction:**
- Repository metadata (name, description, language)
- File structure and directory tree
- Key files: README, package.json/requirements.txt, main config files
- Dependency lists
- Top 20 most relevant files (by size/importance)

**Implementation:**
- Use PyGithub library for API access
- Fallback to raw Git access for public repos
- Handle rate limiting and authentication

**Output:** Structured summary with file tree and key dependencies

### Web Search Capability

**Service:** `WebSearchService`

**API Provider:** Tavily API (simple, cost-effective, good results)
- Alternative: Serper.dev, DuckDuckGo (free)

**Process:**
1. User provides query OR planner generates query from intent
2. Execute search, get top 10 results
3. Extract: title, snippet, URL
4. LLM summarizes results into key insights

**Output:** Search results + synthesized insights

### File Upload Processing

**Service:** `FileProcessorService`

**Supported Formats:**
- PDFs (PyPDF2)
- Text/Code files (direct read)
- DOCX (python-docx) - optional for v1

**Process:**
1. Extract raw content
2. Chunk into sections (for large files)
3. Generate brief summary using LLM

**Output:** File content + summary + metadata

**Constraints:**
- Max file size: 10MB
- Whitelisted file types: .pdf, .txt, .md, .py, .js, .ts, .json, .yaml

## Data Flow

```
User Request → Context Added (optional) → Session Creation
                    ↓                        ↓
              ContextService            Planner
              processes context        analyzes intent
                    ↓                        ↓
            ExternalContext        WITH context
            added to Plan              ↓
                              Better questions & steps
                                      ↓
                              Context-aware execution
```

## Planner Integration

### Prompt Enhancement

The planner prompt will include a new section when external context is available:

```python
def _build_planner_prompt(self, user_intent: str, plan: Plan) -> str:
    base_prompt = self._get_base_prompt()

    context_section = ""
    if plan.external_contexts:
        context_section = "\n=== AVAILABLE CONTEXT ===\n"
        for ctx in plan.external_contexts:
            context_section += f"\n## {ctx.source_type.upper()} Context\n"
            context_section += f"{ctx.content_summary}\n"
        context_section += "\n===========================\n"

    return f"{base_prompt}\n{context_section}\n\nUser Intent: {user_intent}"
```

### Context Usage Points

1. **During `analyze_intent()`** - Planner uses context to understand requirements
2. **During `decompose_into_steps()`** - Planner generates context-aware steps
3. **NOT during execution** - Executor doesn't need full context (just step-specific info)

## API Endpoints

### Add GitHub Context

```python
POST /api/v1/sessions/{session_id}/context/github

Request:
{
  "repo_url": "https://github.com/user/repo"
}

Response:
{
  "context_id": "uuid",
  "status": "added"
}
```

### Add Web Search Context

```python
POST /api/v1/sessions/{session_id}/context/web-search

Request:
{
  "query": "FastAPI best practices 2025"  // optional
}

Response:
{
  "context_id": "uuid",
  "query": "FastAPI best practices 2025"
}
```

### Upload File Context

```python
POST /api/v1/sessions/{session_id}/context/upload

Request: multipart/form-data
- file: <uploaded file>

Response:
{
  "context_id": "uuid",
  "filename": "document.pdf"
}
```

## Error Handling

### GitHub Access Failures
- Private repos → Return error asking for public repo or PAT
- Rate limits → Return error with retry-after time
- Invalid URLs → Validation error

### Web Search Failures
- API quota exceeded → Error message
- No results → Empty context with warning
- Invalid queries → Return error

### File Upload Failures
- Unsupported formats → List supported types
- Size limits (>10MB) → Return error
- Malformed files → Return specific error

### General
- All errors logged with context
- User-friendly error messages
- Never crash on bad context input

## Configuration

**Location:** `src/planweaver/config.py` (extension)

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # GitHub
    github_token: Optional[str] = None  # For private repos

    # Web Search
    tavily_api_key: Optional[str] = None
    search_provider: str = "tavily"  # "tavily", "serper", "duckduckgo"

    # File Upload
    max_file_size_mb: int = 10
    allowed_file_types: List[str] = [
        ".pdf", ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml"
    ]
```

## Testing

### Unit Tests
**File:** `tests/test_context_service.py`

- Mock GitHub API responses → Test repo parsing
- Mock search API → Test result summarization
- Mock file reads → Test content extraction
- Test error handling for each source

### Integration Tests
**File:** `tests/test_context_integration.py`

- Create planning session with GitHub URL
- Verify context appears in planner prompts
- Test that context-aware questions are better
- Test multiple context sources together

### End-to-End Scenarios

1. **GitHub Refactoring**
   - Input: "Refactor GitHub repo to use TypeScript"
   - Add: GitHub context
   - Verify: Planner asks about TypeScript setup
   - Verify: Steps mention specific files from repo

2. **Market Analysis**
   - Input: "Analyze market trend for AI in 2025"
   - Add: Web search context
   - Verify: Planner uses recent information

3. **Document Summary**
   - Input: "Summarize uploaded PDF"
   - Add: File upload
   - Verify: Planner references document content

## Dependencies

### New Python Packages

```toml
[project.dependencies]
# ... existing ...
PyGithub>=2.1.1          # GitHub API
tavily-python>=0.3.0     # Web search API
PyPDF2>=3.0.0            # PDF processing
python-multipart>=0.0.6  # File upload support
```

## Implementation Steps

1. **Phase 1: Foundation**
   - Add `ExternalContext` model
   - Create `context_service.py` skeleton
   - Update orchestrator to handle context
   - Modify planner prompts

2. **Phase 2: GitHub Integration**
   - Implement `GitHubContextAnalyzer`
   - Add GitHub API endpoint
   - Test with sample repositories

3. **Phase 3: Web Search**
   - Implement `WebSearchService`
   - Add search API endpoint
   - Test with various queries

4. **Phase 4: File Uploads**
   - Implement `FileProcessorService`
   - Add file upload endpoint
   - Test with various file types

5. **Phase 5: Testing & Documentation**
   - Write comprehensive tests
   - Update API documentation
   - Add usage examples to README

## Future Enhancements

### Version 2+ Features
- Context caching for frequently used repos
- LLM-based context summarization and filtering
- Context relevance scoring
- Support for more file types (images, spreadsheets)
- Batch context operations
- Context export/import between sessions

### Frontend Integration
- UI for adding context sources
- Visual display of active contexts
- Context management panel
- Real-time context processing status

## Success Criteria

- [ ] All three context sources functional
- [ ] Planner generates better questions with context
- [ ] Context improves step quality
- [ ] Error handling covers all edge cases
- [ ] Test coverage >80%
- [ ] API documented
- [ ] Performance impact minimal (<500ms added to planning)
