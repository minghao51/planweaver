# Reasoning Chains and Self-Correction Design

**Date:** 2025-03-12
**Status:** Design
**Scope:** MVP - Proof of Concept

## Overview

This design adds two interconnected capabilities to PlanWeaver:

1. **Reasoning Chains** - Capture and expose LLM thought processes during planning and execution
2. **Self-Correction** - Autonomous failure recovery using reasoning context

Both features work together: reasoning traces provide the context needed for intelligent self-correction, while self-correction demonstrates the value of captured reasoning.

## Goals

- **Make LLM decision-making visible** - Users see not just WHAT was planned, but WHY
- **Enable autonomous recovery** - Plans adapt to failures without user intervention
- **Maintain simplicity** - Additive changes that don't disrupt existing architecture
- **MVP scope** - Proof of concept with room for enhancement

## Architecture

### System Extension

```
                    User Request
                         ↓
                   Orchestrator
                         ↓
         ┌───────────────┴───────────────┐
         ↓                               ↓
    Planner +                   ExecutionRouter +
    ReasoningEngine            SelfCorrectionService
         ↓                               ↓
         └───────────────┬───────────────┘
                         ↓
                    Enhanced Plans
```

### New Components

**ReasoningEngine** (`src/planweaver/services/reasoning_engine.py`)
- Captures LLM reasoning at every decision point
- Stores structured traces linked to plans/proposals/steps
- Provides reasoning data for frontend display

**SelfCorrectionService** (`src/planweaver/services/self_correction.py`)
- Monitors execution results for failures
- Analyzes failures using reasoning traces
- Generates and applies autonomous corrections

### Database Extensions

**Complete SQL Schema:**

```sql
-- Reasoning traces (planning, proposals, execution)
CREATE TABLE reasoning_traces (
    id VARCHAR(36) PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL,
    proposal_id VARCHAR(36),
    step_id VARCHAR(36),
    trace_type VARCHAR(20) NOT NULL,  -- 'planning' | 'proposal' | 'execution'
    thoughts JSON NOT NULL,  -- List<Thought>
    decisions JSON,  -- List<Decision> (optional)
    confidence_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES execution_steps(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_reasoning_traces_plan_id ON reasoning_traces(plan_id);
CREATE INDEX idx_reasoning_traces_proposal_id ON reasoning_traces(proposal_id);
CREATE INDEX idx_reasoning_traces_step_id ON reasoning_traces(step_id);
CREATE INDEX idx_reasoning_traces_type ON reasoning_traces(trace_type);

-- Autonomous corrections applied during execution
CREATE TABLE corrections (
    id VARCHAR(36) PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL,
    step_id VARCHAR(36) NOT NULL,
    failure_reason TEXT NOT NULL,
    reasoning_used_id VARCHAR(36),
    original_approach JSON NOT NULL,
    corrected_approach JSON NOT NULL,
    correction_rationale TEXT NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL DEFAULT FALSE,

    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES execution_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (reasoning_used_id) REFERENCES reasoning_traces(id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX idx_corrections_plan_id ON corrections(plan_id);
CREATE INDEX idx_corrections_step_id ON corrections(step_id);
CREATE INDEX idx_corrections_success ON corrections(success);
CREATE INDEX idx_corrections_applied_at ON corrections(applied_at);
```

## Data Structures

### ReasoningTrace

```python
ReasoningTrace {
    plan_id: str
    thoughts: List[Thought]
    decision_points: List[Decision]
    confidence: float
}

Thought {
    timestamp: datetime
    content: str
    thought_type: "analysis" | "decision" | "consideration"
    alternatives: List[str]
}

Decision {
    question: str
    options: List[str]
    selected: str
    rationale: str
}
```

### Proposal with Reasoning

```python
Proposal {
    # Existing fields
    steps: List[ExecutionStep]
    title: str
    description: str

    # New fields
    reasoning_trace: ProposalReasoning
    confidence_score: float
    rationale: str  # Human-readable summary
}

ProposalReasoning {
    alternatives_considered: List[str]
    key_decisions: List[Decision]
    trade_offs: Dict[str, str]
    rejected_approaches: List[Tuple[str, str]]  # (approach, reason)
}
```

### StepReasoning

```python
StepReasoning {
    step_id: str
    step_description: str
    thoughts: List[Thought]
    expected_outcome: str
    approach_rationale: str
    alternatives_considered: List[str]
    timestamp: datetime
}
```

### FullReasoningTrace

```python
FullReasoningTrace {
    plan_id: str
    planning_trace: ReasoningTrace
    proposal_traces: Dict[str, ProposalReasoning]  # proposal_id -> reasoning
    step_traces: Dict[str, StepReasoning]  # step_id -> reasoning
    created_at: datetime
    updated_at: datetime
}
```

### Correction-Related Types

```python
class StepResult(BaseModel):
    step_id: str
    status: "success" | "failure" | "partial"
    output: Optional[str]
    error: Optional[str]
    retry_count: int
    execution_time: float

class Correction(BaseModel):
    correction_id: str
    step_id: str
    modification_type: "prompt_template" | "model" | "parameters" | "strategy"
    original_value: Dict[str, Any]
    corrected_value: Dict[str, Any]
    rationale: str

class CorrectionAnalysis(BaseModel):
    failure_cause: str
    suggested_correction_type: str
    confidence: float
    reasoning_context_used: str
    alternative_approaches: List[str]

class CorrectionResult(BaseModel):
    success: bool
    correction_applied: bool
    new_step_status: Optional[StepResult]
    error_message: Optional[str]
    retry_count: int
```

### Existing Type References

```python
# From existing codebase (referenced for completeness)
class LLMResponse(BaseModel):
    content: str
    model: str
    tokens_used: int
    finish_reason: str
    raw_response: Optional[Dict[str, Any]]

class ExecutionStep(BaseModel):
    id: str
    step_type: str
    prompt_template: str
    assigned_model: str
    parameters: Dict[str, Any]
    dependencies: List[str]
```

## Data Flow

### Planning Phase with Visible Reasoning

```
1. User submits intent
   ↓
2. Orchestrator calls Planner
   ↓
3. ReasoningEngine captures planning context:
   - User intent analysis
   - Context sources used (GitHub, web search, etc.)
   - Initial thoughts about approach
   ↓
4. Planner generates clarifying questions
   → ReasoningEngine captures: "Why these questions?"
   ↓
5. User answers questions
   ↓
6. Planner generates proposals (2-3 approaches)
   → ReasoningEngine captures per-proposal:
     - Alternatives considered
     - Key decisions made
     - Trade-offs analyzed
     - Confidence score
   ↓
7. Frontend displays proposals with reasoning
   - Each proposal card shows rationale
   - User can expand full reasoning trace
   ↓
8. User selects proposal
   ↓
9. Orchestrator creates execution plan with embedded reasoning
```

### Execution Phase with Self-Correction

```
1. ExecutionRouter executes steps in DAG order
   ↓
2. For each step:
   a. Execute step
   b. ReasoningEngine captures:
      - What step is doing
      - Expected outcome
      - LLM's thinking process
   ↓
3. On step completion:
   ↓
   ├─ SUCCESS → Continue to next step
   ↓
   └─ FAILURE → SelfCorrectionService:
      a. Retrieve step's reasoning trace
      b. Analyze failure using reasoning context
      c. Generate correction:
         - "Original approach failed because..."
         - "New approach: ..."
         - Modified parameters/strategy
      d. Apply correction autonomously
      e. Log correction to audit trail
      f. Retry step with correction
      ↓
4. Continue until completion or max retries
```

## Integration Details

### Planner Integration

**Location:** `src/planweaver/services/planner.py`

**Integration Point 1: After Intent Analysis**
```python
class Planner:
    async def analyze_intent(self, intent: str) -> IntentAnalysis:
        # Existing intent analysis
        analysis = await self._llm.analyze(intent)

        # NEW: Capture reasoning about intent
        await self.reasoning_engine.capture_planning_reasoning(
            intent=intent,
            context=self.context,
            alternatives_considered=[]  # None yet
        )

        return analysis
```

**Integration Point 2: After Proposal Generation**
```python
class Planner:
    async def generate_strawman_proposals(self, ...) -> List[Proposal]:
        # Existing proposal generation
        proposals = await self._generate_proposals(...)

        # NEW: Capture reasoning for each proposal
        for proposal in proposals:
            await self.reasoning_engine.capture_proposal_reasoning(
                proposal=proposal,
                rejected_alternatives=proposal.metadata.get("rejected", []),
                rationale=proposal.metadata.get("rationale", "")
            )

        return proposals
```

### ExecutionRouter Integration

**Location:** `src/planweaver/services/router.py`

**Integration Point 1: Before Step Execution**
```python
class ExecutionRouter:
    async def execute_step(self, step: ExecutionStep) -> StepResult:
        # NEW: Capture reasoning before execution
        reasoning = await self.reasoning_engine.capture_step_reasoning(
            step=step,
            llm_response=None  # Will be filled after execution
        )

        # Existing step execution
        result = await self._execute_with_retries(step)

        return result
```

**Integration Point 2: On Failure - Self-Correction**
```python
class ExecutionRouter:
    async def _execute_with_retries(self, step: ExecutionStep) -> StepResult:
        retry_count = 0
        max_retries = 3  # Existing retry logic

        while retry_count < max_retries:
            result = await self._execute_step(step)

            if result.status == "success":
                return result

            # NEW: Try self-correction before giving up
            if retry_count < max_retries - 1:  # Don't correct on last retry
                correction_result = await self.self_correction.attempt_correction(
                    step=step,
                    result=result,
                    reasoning_trace=await self.reasoning_engine.get_step_reasoning(step.id)
                )

                if correction_result.success:
                    step = self._apply_correction_to_step(step, correction_result.correction)
                    retry_count += 1
                    continue

            retry_count += 1

        return result  # Failed after all retries

    def _apply_correction_to_step(self, step: ExecutionStep, correction: Correction) -> ExecutionStep:
        """Apply correction to step for retry."""
        if correction.modification_type == "prompt_template":
            step.prompt_template = correction.corrected_value["prompt_template"]
        elif correction.modification_type == "model":
            step.assigned_model = correction.corrected_value["model"]
        elif correction.modification_type == "parameters":
            step.parameters.update(correction.corrected_value["parameters"])
        elif correction.modification_type == "strategy":
            step.strategy = correction.corrected_value["strategy"]

        return step
```

### Orchestrator Integration

**Location:** `src/planweaver/orchestrator.py`

**Initialization:**
```python
class Orchestrator:
    def __init__(self):
        # Existing services
        self.planner = Planner(...)
        self.execution_router = ExecutionRouter(...)

        # NEW: Initialize reasoning and correction services
        self.reasoning_engine = ReasoningEngine(db_session)
        self.self_correction = SelfCorrectionService(
            db_session=db_session,
            reasoning_engine=self.reasoning_engine,
            llm_gateway=self.llm_gateway
        )

        # Wire services together
        self.planner.reasoning_engine = self.reasoning_engine
        self.execution_router.reasoning_engine = self.reasoning_engine
        self.execution_router.self_correction = self.self_correction
```

## Component APIs

### ReasoningEngine

```python
class ReasoningEngine:
    async def capture_planning_reasoning(
        intent: str,
        context: Context,
        alternatives_considered: List[Proposal]
    ) -> ReasoningTrace

    async def capture_proposal_reasoning(
        proposal: Proposal,
        rejected_alternatives: List[str],
        rationale: str
    ) -> ProposalReasoning

    async def capture_step_reasoning(
        step: ExecutionStep,
        llm_response: LLMResponse
    ) -> StepReasoning

    def get_trace(plan_id: str) -> FullReasoningTrace
    def get_proposal_reasoning(proposal_id: str) -> ProposalReasoning
    def get_step_reasoning(step_id: str) -> StepReasoning
```

### SelfCorrectionService

```python
class SelfCorrectionService:
    MAX_CORRECTION_ATTEMPTS = 3

    async def analyze_failure(
        step_result: StepResult,
        reasoning_trace: StepReasoning
    ) -> CorrectionAnalysis

    async def generate_correction(
        failed_step: ExecutionStep,
        analysis: CorrectionAnalysis
    ) -> Correction

    async def apply_correction(
        plan_id: str,
        step_id: str,
        correction: Correction
    ) -> CorrectionResult

    async def should_correct(
        step_result: StepResult
    ) -> bool
```

## Frontend Components

### ReasoningPanel

Displays reasoning traces with expandable thoughts and decisions.

```typescript
interface ReasoningPanelProps {
  trace: ReasoningTrace;
  variant: "proposal" | "execution";
}

// Displays:
// - Timeline of thoughts
// - Decision points with alternatives
// - Confidence indicators
// - Expandable details for each thought
```

### ProposalCard Enhancement

Add reasoning visibility to existing proposal cards.

```typescript
interface ProposalCardProps {
  proposal: Proposal;
  reasoning: ProposalReasoning;
  showReasoning?: boolean;
}

// Additions:
// - "View Reasoning" toggle
// - Rationale summary card
// - Trade-offs considered
// - Confidence meter
```

### CorrectionTimeline

Shows autonomous corrections applied during execution.

```typescript
interface CorrectionTimelineProps {
  corrections: Correction[];
  planId: string;
}

// Shows:
// - When corrections were applied
// - What was changed
// - Why (with reasoning link)
// - Success/failure of correction
```

### QuestionPanel Enhancement

When showing clarifying questions, include reasoning about why each question is being asked.

```typescript
interface QuestionPanelProps {
  questions: Question[];
  questionReasoning: Map<string, QuestionReasoning>;
}

// Additions:
// - "Why am I asking this?" for each question
// - Context that triggered the question
```

## API Endpoints

```python
# Reasoning traces
GET /api/plans/{plan_id}/reasoning
GET /api/proposals/{proposal_id}/reasoning
GET /api/steps/{step_id}/reasoning

# Corrections
GET /api/plans/{plan_id}/corrections
POST /api/plans/{plan_id}/corrections/{correction_id}/revert

# UI integration
GET /api/plans/{plan_id}/with-reasoning  # Full plan + traces
```

### API Request/Response Schemas

**GET /api/plans/{plan_id}/reasoning**

Response:
```json
{
  "plan_id": "string",
  "planning_trace": {
    "id": "string",
    "thoughts": [
      {
        "timestamp": "2025-03-12T10:00:00Z",
        "content": "string",
        "thought_type": "analysis|decision|consideration",
        "alternatives": ["string"]
      }
    ],
    "decisions": [
      {
        "question": "string",
        "options": ["string"],
        "selected": "string",
        "rationale": "string"
      }
    ],
    "confidence_score": 0.95
  },
  "proposal_traces": {
    "proposal_id": {
      "alternatives_considered": ["string"],
      "key_decisions": [...],
      "trade_offs": {"key": "value"},
      "rejected_approaches": [["approach", "reason"]]
    }
  }
}
```

**GET /api/proposals/{proposal_id}/reasoning**

Response:
```json
{
  "proposal_id": "string",
  "reasoning": {
    "alternatives_considered": ["string"],
    "key_decisions": [...],
    "trade_offs": {"key": "value"},
    "rejected_approaches": [["approach", "reason"]],
    "confidence_score": 0.85
  }
}
```

**GET /api/steps/{step_id}/reasoning**

Response:
```json
{
  "step_id": "string",
  "step_description": "string",
  "thoughts": [...],
  "expected_outcome": "string",
  "approach_rationale": "string",
  "alternatives_considered": ["string"],
  "timestamp": "2025-03-12T10:00:00Z"
}
```

**GET /api/plans/{plan_id}/corrections**

Response:
```json
{
  "plan_id": "string",
  "corrections": [
    {
      "id": "string",
      "step_id": "string",
      "failure_reason": "string",
      "reasoning_used_id": "string",
      "original_approach": {...},
      "corrected_approach": {...},
      "correction_rationale": "string",
      "applied_at": "2025-03-12T10:00:00Z",
      "success": true
    }
  ]
}
```

**POST /api/plans/{plan_id}/corrections/{correction_id}/revert**

Request:
```json
{
  "reason": "string (optional)"
}
```

Response:
```json
{
  "success": true,
  "message": "Correction reverted successfully"
}
```

**GET /api/plans/{plan_id}/with-reasoning**

Response:
```json
{
  "plan": {...},  // Full plan object (existing structure)
  "reasoning": {
    "planning_trace": {...},
    "proposal_traces": {...},
    "step_traces": {...}
  },
  "corrections": [...]
}
```

## Self-Correction Algorithm

### Correction Generation Logic

```python
class SelfCorrectionService:
    async def attempt_correction(
        self,
        step: ExecutionStep,
        result: StepResult,
        reasoning_trace: StepReasoning
    ) -> CorrectionResult:

        # 1. Check if we should attempt correction
        if not await self.should_correct(result):
            return CorrectionResult(success=False, correction_applied=False)

        # 2. Analyze the failure
        analysis = await self.analyze_failure(result, reasoning_trace)

        # 3. Generate correction
        correction = await self.generate_correction(step, analysis)

        # 4. Validate correction
        if not self._validate_correction(correction):
            logger.warning(f"Invalid correction generated: {correction}")
            return CorrectionResult(
                success=False,
                correction_applied=False,
                error_message="Correction validation failed"
            )

        # 5. Check retry limit
        attempt_count = await self._get_correction_count(step.id)
        if attempt_count >= self.MAX_CORRECTION_ATTEMPTS:
            return CorrectionResult(
                success=False,
                correction_applied=False,
                error_message="Max correction attempts reached"
            )

        # 6. Apply and log correction
        try:
            result = await self.apply_correction(step.plan_id, step.id, correction)
            await self._log_correction(step, correction, result)
            return result
        except Exception as e:
            logger.error(f"Failed to apply correction: {e}")
            return CorrectionResult(
                success=False,
                correction_applied=False,
                error_message=str(e)
            )
```

### When NOT to Correct

```python
async def should_correct(self, step_result: StepResult) -> bool:
    """
    Determines whether a failure should trigger self-correction.
    """

    # Don't correct if:
    # 1. Step was manually cancelled by user
    if step_result.status == "cancelled":
        return False

    # 2. Error is not recoverable (e.g., auth failure, invalid API key)
    unrecoverable_errors = [
        "authentication",
        "authorization",
        "invalid_api_key",
        "quota_exceeded",
        "network_unreachable"
    ]
    if step_result.error and any(err in step_result.error.lower() for err in unrecoverable_errors):
        return False

    # 3. Too many retries already
    if step_result.retry_count >= 2:  # Leave room for correction retries
        return False

    # 4. Step completed but with partial success (let user decide)
    if step_result.status == "partial":
        return False

    return True
```

## LLM Integration Strategy

### Capturing Reasoning from LLMs

**Approach:** Prompt Engineering + Structured Response Parsing

We'll use structured prompting to elicit reasoning from LLMs:

```python
async def capture_proposal_reasoning(self, proposal: Proposal, ...) -> ProposalReasoning:
    """
    Captures reasoning by explicitly requesting it from the LLM.
    """

    prompt = f"""
    Generate a proposal for: {user_intent}

    IMPORTANT: You must provide your reasoning process.

    Respond in this JSON structure:
    {{
        "proposal": {{
            "title": "...",
            "steps": [...]
        }},
        "reasoning": {{
            "alternatives_considered": [
                "Describe an alternative approach you considered"
            ],
            "key_decisions": [
                {{
                    "question": "What decision did you make?",
                    "options": ["option1", "option2"],
                    "selected": "option1",
                    "rationale": "Why did you choose this?"
                }}
            ],
            "trade_offs": {{
                "aspect": "trade-off description"
            }},
            "rejected_approaches": [
                ["approach name", "why you rejected it"]
            ],
            "confidence_score": 0.8
        }}
    }}
    """

    response = await self.llm_gateway.complete(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    parsed = json.loads(response.content)
    return ProposalReasoning(**parsed["reasoning"])
```

**Fallback Strategy:** If model doesn't support structured reasoning:
```python
try:
    reasoning = await self._capture_structured_reasoning(...)
except Exception as e:
    logger.warning(f"Structured reasoning failed: {e}")
    # Fallback: Basic summary
    reasoning = ProposalReasoning(
        alternatives_considered=["Not available"],
        key_decisions=[],
        trade_offs={},
        rejected_approaches=[],
        confidence_score=0.5
    )
```

## Migration Strategy

### Backward Compatibility

**Approach:** Non-breaking, additive changes

1. **New tables are optional:** Plans without reasoning traces continue to work
2. **Feature flags:** Enable/disable reasoning and correction independently
3. **Gradual rollout:** Test on subset of plans before full deployment

### Migration Steps

```sql
-- Step 1: Add new tables (safe, doesn't affect existing data)
CREATE TABLE reasoning_traces (...);
CREATE TABLE corrections (...);

-- Step 2: Add feature flags to configuration
ALTER TABLE plans ADD COLUMN reasoning_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE plans ADD COLUMN correction_enabled BOOLEAN DEFAULT TRUE;
```

### Handling Existing Data

**Plans without reasoning:**
- Frontend shows: "Reasoning not available for this plan"
- Execution continues without self-correction
- No breaking changes to existing workflows

**Existing execution logs:**
- Remain unchanged
- New corrections only apply to future executions
- Optional: Backfill reasoning for historical plans (offline job)

## Error Handling

### Reasoning Capture Failures

- **Strategy:** Graceful degradation
- **Behavior:** Log warning, continue without reasoning
- **User Impact:** "Reasoning not available" message in UI
- **Principle:** Reasoning is enrichment, not a requirement

### Self-Correction Failures

- **Maximum retry limit:** 3 correction attempts per step
- **Fallback:** Fail the step after max retries
- **Safety:** Validate corrections before applying
- **Audit:** Always log corrections, successful or not

### Large Reasoning Traces

- **Detection:** Configurable size threshold
- **Strategy:** Summarize + external storage
- **UI:** Pagination for large traces
- **Retention:** Configurable (default: 30 days for full traces)

### Concurrent Corrections

- **Strategy:** Queue corrections per plan (serial processing)
- **Priority:** Based on DAG position (upstream first)
- **Locking:** One correction active per plan at a time

## Testing Strategy

### Unit Tests

**ReasoningEngine:**
- Capture planning/proposal/step reasoning
- Trace retrieval and serialization
- Confidence score calculation
- Malformed response handling

**SelfCorrectionService:**
- Failure analysis with reasoning context
- Correction generation
- Application and retry logic
- Max retry enforcement
- Correction validation

**Database Models:**
- Trace and correction creation
- Propagation to proposals/steps
- History retrieval

### Integration Tests

**Planning Flow:**
- Full planning with reasoning capture
- Proposal selection with visible reasoning
- Trace persistence across session
- API endpoint functionality

**Execution Flow:**
- Step failure triggers correction
- Correction uses reasoning context
- Successful correction continues execution
- Failed correction respects retry limit
- Multiple corrections in single plan
- Correction timeline visibility

### Frontend Tests

**Component Tests (Vitest):**
- ReasoningPanel rendering and interaction
- ProposalCard reasoning expansion
- CorrectionTimeline display
- OptimizerStage integration

**E2E Tests (Playwright):**
- Proposal shows reasoning
- Reasoning expands/collapses
- Reasoning persists on reload
- Correction applies during execution
- Correction shows in timeline
- Failed correction displays error

### Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| ReasoningEngine | 90%+ |
| SelfCorrectionService | 90%+ |
| Database models | 85%+ |
| API endpoints | 85%+ |
| Frontend components | 80%+ |
| E2E flows | Key user journeys |

## Implementation Phases

### Phase 1: Reasoning Foundation

1. Create database models and migrations
2. Implement ReasoningEngine service
3. Integrate with Planner for proposal reasoning
4. Create ReasoningPanel frontend component
5. Add reasoning to ProposalCard
6. Write unit and integration tests

### Phase 2: Execution Reasoning

1. Capture step-level reasoning during execution
2. Enhance ReasoningPanel for execution traces
3. Add reasoning API endpoints
4. Create step reasoning UI components
5. Write tests

### Phase 3: Self-Correction

1. Implement SelfCorrectionService
2. Integrate with ExecutionRouter
3. Add failure detection and analysis
4. Implement correction generation and application
5. Create CorrectionTimeline component
6. Add correction API endpoints
7. Write tests

### Phase 4: Polish and Integration

1. Performance optimization (large traces)
2. Enhanced error handling
3. UI/UX improvements
4. Documentation updates
5. End-to-end testing

## Success Criteria

- Users can see reasoning traces for every proposal
- Users can understand WHY specific approaches were suggested
- Failed steps trigger autonomous corrections
- Corrections use reasoning context for better decisions
- All corrections logged and visible in UI
- System gracefully handles reasoning/correction failures
- Test coverage meets targets
- No degradation in existing functionality

## Future Enhancements

Beyond MVP:

1. **Learning from corrections** - Build knowledge base of successful patterns
2. **User feedback on reasoning** - Allow users to rate/correct reasoning quality
3. **Collaborative reasoning** - Multiple users can discuss and refine reasoning
4. **Reasoning templates** - Reusable reasoning patterns for common tasks
5. **Explainable AI** - Natural language explanations of technical reasoning
6. **Correction suggestions** - Propose corrections for user approval before applying
