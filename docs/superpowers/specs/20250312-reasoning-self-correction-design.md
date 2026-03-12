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

**New Tables:**

```sql
-- Reasoning traces (planning, proposals, execution)
reasoning_traces
├── id (PK)
├── plan_id (FK)
├── proposal_id (FK, nullable)
├── step_id (FK, nullable)
├── trace_type (planning | proposal | execution)
├── thoughts (JSON) - List<Thought>
├── decisions (JSON) - List<Decision>
├── confidence_score
├── created_at

-- Autonomous corrections applied during execution
corrections
├── id (PK)
├── plan_id (FK)
├── step_id (FK)
├── failure_reason
├── reasoning_used (FK to reasoning_traces)
├── original_approach (JSON)
├── corrected_approach (JSON)
├── correction_rationale
├── applied_at
├── success (boolean)
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
