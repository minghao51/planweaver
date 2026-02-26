# Plan Comparison Feature Design

**Date:** 2026-02-26
**Status:** Approved
**Complexity:** Medium
**Estimated Duration:** 7-10 days

---

## Overview

The Plan Comparison feature enables users to compare multiple strawman proposals side-by-side before committing to execution. Users can see execution steps, cost/time estimates, and risk assessments to make informed decisions between different approaches.

**Key Benefit:** Transforms the proposal selection process from a guessing game into an informed decision by providing transparent comparisons of what each approach actually entails.

---

## Current State

**Planning Flow (Before):**
1. User submits intent → Clarifying questions
2. System generates 2-3 strawman proposals (title, description, approach, pros/cons)
3. User selects one proposal based on limited information
4. System generates execution graph for selected proposal
5. User approves and executes

**Problem:**
- Users can't see actual execution steps before selecting
- No visibility into cost/time differences between proposals
- Hard to compare "riskier" vs "safer" approaches concretely
- Selection based on abstract descriptions, not concrete execution plans

---

## Proposed Solution

**Planning Flow (After):**
1. User submits intent → Clarifying questions
2. System generates 2-3 proposals **with lightweight analysis** (step count, complexity, time, cost, risks)
3. User can **click "Compare"** to see detailed comparison with execution graphs
4. User selects proposal with full understanding of differences
5. System generates execution graph (cached if already viewed in comparison)
6. User approves and executes

**Key Innovation:** Hybrid generation strategy
- Lightweight analysis upfront (fast, cheap, included in proposal generation)
- Full execution graphs on-demand (only when user wants to compare)
- Caching avoids regeneration

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend                                │
│  ┌──────────────┐  ┌──────────────────────────────────┐    │
│  │  PlanView    │  │  ProposalComparisonView           │    │
│  │              │  │  ├── DiffComparison (default)     │    │
│  │  Proposals   │  │  └── SideBySideComparison (exp.)  │    │
│  │  [Compare]   │  │                                   │    │
│  └──────────────┘  └──────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│  POST /api/v1/sessions/{id}/compare-proposals               │
│    Request: {proposal_ids: [1, 2]}                          │
│    Response: ProposalComparison                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │ Planner (enhanced)   │  │ ProposalComparisonService    │ │
│  │                      │  │                              │ │
│  │ generate_strawman    │  │ compare_proposals()          │ │
│  │ _analyze_lightweight │  │ _find_common_steps()         │ │
│  └──────────────────────┘  │ _estimate_cost()             │ │
│                            │ _estimate_time()              │ │
│                            │ _graph_cache                  │ │
│                            └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLM Gateway                             │
│  LiteLLM (gemini-2.5-flash for analysis)                    │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

**Lightweight Analysis (During Proposal Generation):**
```
1. Planner.generate_strawman_proposals()
2. LLM generates: title, description, approach, pros, cons
3. LLM analyzes: step_count, complexity, time, cost, risks (single call)
4. Returns: List[ProposalWithAnalysis]
5. Frontend displays: Quick metrics cards
```

**Detailed Comparison (On User Request):**
```
1. User clicks "Compare" and selects proposals to compare
2. API: POST /compare-proposals?proposal_ids=[1,2]
3. ComparisonService:
   a. Check cache for execution graphs
   b. Generate uncached graphs via Planner.decompose_into_steps()
   c. Compute diff between proposals
   d. Calculate accurate time/cost estimates
4. Return: ProposalComparison with full graphs + diff
5. Frontend displays: Diff view or side-by-side view
```

---

## Data Models

### Enhanced Proposal

```python
class ProposalWithAnalysis(BaseModel):
    """Proposal with quick analysis (shown by default)"""

    # Existing fields
    proposal_id: int
    title: str
    description: str
    approach: str
    pros: List[str]
    cons: List[str]

    # New lightweight fields
    estimated_step_count: int           # e.g., 6
    complexity_score: str               # "Low" | "Medium" | "High"
    estimated_time_minutes: int         # e.g., 15
    estimated_cost_usd: Decimal         # e.g., 0.05
    risk_factors: List[str]             # ["External API dependency"]
```

### Comparison Response

```python
class ProposalComparison(BaseModel):
    """Detailed comparison of selected proposals"""

    session_id: str
    proposals: List[ProposalDetail]

    # Diff analysis
    common_steps: List[StepSummary]
    unique_steps_by_proposal: Dict[int, List[StepSummary]]

    # Comparison metrics
    time_comparison: Dict[int, int]           # proposal_id -> minutes
    cost_comparison: Dict[int, Decimal]       # proposal_id -> USD
    complexity_comparison: Dict[int, str]     # proposal_id -> score

class ProposalDetail(BaseModel):
    """Full proposal with execution graph"""

    proposal_id: int
    full_execution_graph: List[ExecutionStep]
    accurate_time_estimate: int
    accurate_cost_estimate: Decimal
    all_risk_factors: List[str]
    generation_error: Optional[str]           # If generation failed

class StepSummary(BaseModel):
    """Simplified step for comparison display"""

    task: str
    complexity: str
    estimated_time_minutes: int
```

---

## API Specification

### Compare Proposals

**Endpoint:** `POST /api/v1/sessions/{session_id}/compare-proposals`

**Request:**
```json
{
  "proposal_ids": [1, 2]
}
```

**Response (200 OK):**
```json
{
  "session_id": "abc-123",
  "proposals": [
    {
      "proposal_id": 1,
      "full_execution_graph": [
        {
          "step_id": "step-1",
          "task": "Backup database",
          "assigned_model": "gemini-2.5-flash",
          "dependencies": []
        }
      ],
      "accurate_time_estimate": 18,
      "accurate_cost_estimate": "0.08",
      "all_risk_factors": ["Data consistency during migration"]
    }
  ],
  "common_steps": [
    {"task": "Backup database", "complexity": "Low"}
  ],
  "unique_steps_by_proposal": {
    "1": [
      {"task": "Create migration script", "complexity": "Medium"}
    ],
    "2": [
      {"task": "Stop production", "complexity": "Low"}
    ]
  },
  "time_comparison": {"1": 18, "2": 12},
  "cost_comparison": {"1": "0.08", "2": "0.15"},
  "complexity_comparison": {"1": "Medium", "2": "High"}
}
```

**Error Responses:**

- `404 Not Found` - Invalid proposal IDs
- `400 Bad Request` - Less than 2 proposals provided
- `500 Internal Server Error` - LLM generation failure

---

## Implementation Details

### 1. Enhanced Planner

**File:** `src/planweaver/services/planner.py`

**Changes:**
```python
class Planner:
    async def generate_strawman_proposals(
        self,
        plan: Plan
    ) -> List[ProposalWithAnalysis]:
        """Generate proposals with lightweight analysis"""

        # Generate base proposals
        raw_proposals = await self._generate_proposals_raw(plan)

        # Add lightweight analysis (single LLM call)
        analysis = await self._analyze_proposals_lightweight(
            plan=plan,
            proposals=raw_proposals
        )

        # Merge and return
        return [
            ProposalWithAnalysis(
                **p.dict(),
                **analysis[p['proposal_id']]
            )
            for p in raw_proposals
        ]

    async def _analyze_proposals_lightweight(
        self,
        plan: Plan,
        proposals: List[dict]
    ) -> Dict:
        """Quick analysis without full execution graph"""

        prompt = f"""
        Analyze these proposals for: {plan.user_intent}

        Proposals:
        {self._format_proposals(proposals)}

        For EACH proposal, estimate:
        1. Step count (number)
        2. Complexity (Low/Medium/High)
        3. Estimated time (minutes, ~2min/step)
        4. Estimated cost (USD, ~$0.001/step)
        5. Risk factors (list 2-3 specific risks)

        Return JSON: {{"proposal_1": {...}, "proposal_2": {...}}}
        """

        response = await self.llm_gateway.complete(
            prompt=prompt,
            model="gemini-2.5-flash"  # Fast, cost-effective
        )

        return parse_json_response(response)
```

### 2. Comparison Service

**File:** `src/planweaver/services/comparison_service.py` (new)

```python
class ProposalComparisonService:
    def __init__(self, planner: Planner, llm_gateway: LLMGateway):
        self.planner = planner
        self.llm = llm_gateway
        self._graph_cache: Dict[Tuple[str, int], List[ExecutionStep]] = {}

    async def compare_proposals(
        self,
        plan: Plan,
        proposal_ids: List[int]
    ) -> ProposalComparison:
        """Generate detailed comparison on-demand"""

        # Validate
        if len(proposal_ids) < 2:
            raise ValueError("Need at least 2 proposals")

        # Generate full execution graphs
        proposal_details = []
        for prop_id in proposal_ids:
            graph = await self._generate_or_get_execution_graph(plan, prop_id)
            time_est = self._estimate_time(graph)
            cost_est = await self._estimate_cost(graph)
            risks = self._extract_risks(graph)

            proposal_details.append(ProposalDetail(
                proposal_id=prop_id,
                full_execution_graph=graph,
                accurate_time_estimate=time_est,
                accurate_cost_estimate=cost_est,
                all_risk_factors=risks
            ))

        # Compute diff
        common_steps = self._find_common_steps(proposal_details)
        unique_steps = self._find_unique_steps(proposal_details)

        # Build comparison
        return ProposalComparison(
            session_id=plan.session_id,
            proposals=proposal_details,
            common_steps=common_steps,
            unique_steps_by_proposal=unique_steps,
            time_comparison={p.proposal_id: p.accurate_time_estimate
                           for p in proposal_details},
            cost_comparison={p.proposal_id: p.accurate_cost_estimate
                           for p in proposal_details},
            complexity_comparison={p.proposal_id: self._score_complexity(p)
                                  for p in proposal_details}
        )

    async def _generate_or_get_execution_graph(
        self,
        plan: Plan,
        proposal_id: int
    ) -> List[ExecutionStep]:
        """Generate or retrieve cached execution graph"""

        cache_key = (plan.session_id, proposal_id)

        if cache_key in self._graph_cache:
            return self._graph_cache[cache_key]

        # Generate graph
        proposal = plan.get_proposal(proposal_id)
        graph = await self.planner.decompose_into_steps(plan, proposal)

        # Cache for 10 minutes
        self._graph_cache[cache_key] = graph
        asyncio.create_task(self._expire_cache(cache_key, 600))

        return graph

    def _find_common_steps(
        self,
        proposals: List[ProposalDetail]
    ) -> List[StepSummary]:
        """Find steps common to all proposals (with fuzzy matching)"""

        # Use embedding similarity for fuzzy matching
        # Steps with >0.85 similarity considered "common"
        # Return only steps present in ALL proposals
        pass

    def _find_unique_steps(
        self,
        proposals: List[ProposalDetail]
    ) -> Dict[int, List[StepSummary]]:
        """Find steps unique to each proposal"""
        pass

    def _estimate_time(self, steps: List[ExecutionStep]) -> int:
        """Estimate execution time in minutes"""

        base_time_per_step = 2  # minutes
        complexity_multiplier = {"Low": 1.0, "Medium": 1.5, "High": 2.5}

        total = 0
        for step in steps:
            complexity = self._infer_step_complexity(step)
            total += base_time_per_step * complexity_multiplier[complexity]

        return int(total)

    async def _estimate_cost(self, steps: List[ExecutionStep]) -> Decimal:
        """Estimate execution cost in USD"""

        tokens_per_step = 500
        pricing = {
            "gemini-2.5-flash": 0.075,  # $0.075 per 1M tokens
            "deepseek-chat": 0.14,
            "claude-3.5-sonnet": 3.0,
        }

        total_tokens = len(steps) * tokens_per_step
        model = steps[0].assigned_model if steps else "gemini-2.5-flash"

        cost = (total_tokens / 1_000_000) * pricing.get(model, 0.15)

        return Decimal(str(round(cost, 4)))
```

### 3. API Endpoint

**File:** `src/planweaver/api/routers/sessions.py`

```python
@router.post("/sessions/{session_id}/compare-proposals")
async def compare_proposals(
    session_id: str,
    request: ComparisonRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    comparison_service: ProposalComparisonService = Depends(get_comparison_service)
):
    """Compare detailed execution graphs for proposals"""

    plan = await orchestrator.get_plan(session_id)

    # Validate proposal IDs
    valid_ids = {p.id for p in plan.proposals}
    invalid_ids = set(request.proposal_ids) - valid_ids

    if invalid_ids:
        raise HTTPException(
            404,
            f"Proposals not found: {invalid_ids}. Valid IDs: {valid_ids}"
        )

    if len(request.proposal_ids) < 2:
        raise HTTPException(
            400,
            f"Comparison requires at least 2 proposals. Got {len(request.proposal_ids)}"
        )

    comparison = await comparison_service.compare_proposals(
        plan=plan,
        proposal_ids=request.proposal_ids
    )

    return comparison
```

### 4. Frontend Components

**File:** `frontend/src/components/ProposalComparisonView.tsx` (new)

```typescript
interface ProposalComparisonViewProps {
  session: Session;
  proposals: ProposalWithAnalysis[];
  onClose: () => void;
  onSelectProposal: (proposalId: number) => void;
}

function ProposalComparisonView({
  session,
  proposals,
  onClose,
  onSelectProposal
}: Props) {
  const [comparison, setComparison] = useState<ProposalComparison | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCompare = async (proposalIds: number[]) => {
    setError(null);
    setLoading(true);

    try {
      const result = await api.compareProposals(session.id, proposalIds);
      setComparison(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="comparison-view">
      <div className="comparison-header">
        <h2>Compare Proposals</h2>
        <button onClick={onClose}>✕</button>
      </div>

      {error && <ErrorMessage message={error} />}
      {loading && <Spinner />}

      {!comparison ? (
        <ProposalSelector
          proposals={proposals}
          onCompare={handleCompare}
        />
      ) : isExpanded ? (
        <SideBySideComparison
          comparison={comparison}
          onSelectProposal={onSelectProposal}
        />
      ) : (
        <DiffComparison
          comparison={comparison}
          onExpand={() => setIsExpanded(true)}
          onSelectProposal={onSelectProposal}
        />
      )}
    </div>
  );
}
```

**File:** `frontend/src/components/DiffComparison.tsx` (new)

```typescript
function DiffComparison({
  comparison,
  onExpand,
  onSelectProposal
}: Props) {
  const proposals = comparison.proposals;

  return (
    <div className="diff-comparison">
      {/* Quick metrics cards */}
      <div className="quick-metrics">
        {proposals.map(p => (
          <MetricCard
            key={p.proposal_id}
            proposal={p}
            time={comparison.time_comparison[p.proposal_id]}
            cost={comparison.cost_comparison[p.proposal_id]}
            complexity={comparison.complexity_comparison[p.proposal_id]}
            onSelect={() => onSelectProposal(p.proposal_id)}
          />
        ))}
      </div>

      {/* Toggle button */}
      <button onClick={onExpand}>
        Show All Side-by-Side ▼
      </button>

      {/* Common steps */}
      <StepSection
        title="Common Steps"
        steps={comparison.common_steps}
        icon="✓"
      />

      {/* Unique steps per proposal */}
      {proposals.map(p => (
        <StepSection
          key={p.proposal_id}
          title={`Unique to Proposal ${p.proposal_id}`}
          steps={comparison.unique_steps_by_proposal[p.proposal_id]}
          icon="→"
          color={getProposalColor(p.proposal_id)}
        />
      ))}
    </div>
  );
}
```

**File:** `frontend/src/components/PlanView.tsx` (modified)

```typescript
function PlanView({ session }: { session: Session }) {
  const [showComparison, setShowComparison] = useState(false);

  return (
    <div>
      {/* Existing proposal list */}
      <ProposalList proposals={session.proposals}>
        {proposals.map(p => (
          <ProposalCard
            key={p.id}
            proposal={p}
            onSelect={() => handleSelect(p.id)}
          />
        ))}
      </ProposalList>

      {/* NEW: Compare button */}
      {session.proposals.length >= 2 && (
        <button onClick={() => setShowComparison(true)}>
          Compare Proposals ({session.proposals.length} available)
        </button>
      )}

      {/* Comparison modal */}
      {showComparison && (
        <ProposalComparisonView
          session={session}
          proposals={session.proposals}
          onClose={() => setShowComparison(false)}
          onSelectProposal={(id) => {
            handleSelect(id);
            setShowComparison(false);
          }}
        />
      )}
    </div>
  );
}
```

---

## UI Design

### Diff View (Default)

Collapsed view focused on differences:

```
┌─────────────────────────────────────────────────────────────────┐
│  Compare Proposals                                    [✕ Close] │
│  ▼ Show All Side-by-Side                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ⚡ QUICK COMPARISON                                            │
│                                                                 │
│  ┌─────────────────────┬─────────────────────┬────────────────┐│
│  │  Proposal 1         │  Proposal 2         │  Best Value    ││
│  │  Incremental Mig.   │  Big Bang Rewrite   │                ││
│  ├─────────────────────┼─────────────────────┼────────────────┤│
│  │  ⏱ 18 min          │  ⏱ 12 min          │  ⚡ Faster      ││
│  │  💰 $0.08           │  💰 $0.15           │  💰 Cheaper    ││
│  │  ⚠️ Medium risk     │  ⚠️⚠️ High risk     │  ✅ Safer      ││
│  └─────────────────────┴─────────────────────┴────────────────┘│
│                                                                 │
│  📊 COMMON STEPS (2)                                           │
│  ✓ Backup database                                             │
│  ✓ Update dependencies                                         │
│                                                                 │
│  🔵 UNIQUE TO PROPOSAL 1                                       │
│  → Create migration script                                     │
│  → Run pilot test                                              │
│                                                                 │
│  🟢 UNIQUE TO PROPOSAL 2                                       │
│  → Stop production                                             │
│  → Deploy new version                                          │
│                                                                 │
│  [Select Proposal 1]  [Select Proposal 2]                      │
└─────────────────────────────────────────────────────────────────┘
```

### Side-by-Side View (Expanded)

Full execution graphs with all details:

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Compare Proposals                                              [✕ Close] │
│  ▲ Show Differences Only                                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌───────────────────────────────────┬───────────────────────────────────┐│
│  │  🔵 Proposal 1: Incremental Mig.  │  🟢 Proposal 2: Big Bang Rewrite  ││
│  ├───────────────────────────────────┼───────────────────────────────────┤│
│  │  ⏱ 18 minutes                    │  ⏱ 12 minutes                     ││
│  │  💰 $0.08                         │  💰 $0.15                          ││
│  │  ⚠️ Medium risk                   │  ⚠️⚠️ High risk                    ││
│  ├───────────────────────────────────┼───────────────────────────────────┤│
│  │  📋 EXECUTION STEPS (6)           │  📋 EXECUTION STEPS (4)           ││
│  │                                   │                                    ││
│  │  ✓ Backup database                │  ✓ Backup database                 ││
│  │  ✓ Update dependencies            │  ✓ Update dependencies             ││
│  │  → Create migration script 🔵     │  → Stop production 🟢              ││
│  │  → Run pilot test 🔵              │  → Deploy new version 🟢          ││
│  │  → Migrate data 🔵                │  → Verify deployment 🟢           ││
│  │  → Switch traffic 🔵              │                                    ││
│  │                                   │                                    ││
│  │  💡 RISK FACTORS:                 │  💡 RISK FACTORS:                  ││
│  │  • Data consistency during mig.   │  • Production downtime             ││
│  │  • Pilot may miss edge cases      │  • Rollback difficult             ││
│  │                                   │                                    ││
│  │  [SELECT THIS PROPOSAL]           │  [SELECT THIS PROPOSAL]            ││
│  └───────────────────────────────────┴───────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Error Handling

### Error Scenarios

**1. Invalid Proposal IDs**
```python
# Return 404 with helpful message
raise HTTPException(
    404,
    f"Proposals not found: {invalid_ids}. Valid IDs: {valid_ids}"
)
```

**2. LLM Failures During Graph Generation**
```python
# Return partial result with error indicator
return ProposalDetail(
    proposal_id=prop_id,
    full_execution_graph=[],
    accurate_time_estimate=None,
    accurate_cost_estimate=None,
    generation_error="Unable to generate full details. Please try again."
)
```

**3. Single Proposal Comparison**
```python
# Return 400
raise HTTPException(
    400,
    "Comparison requires at least 2 proposals. "
    f"Received {len(proposal_ids)} proposal(s)."
)
```

**4. Cost Estimation Unknown Model**
```python
# Fallback to conservative estimate
try:
    pricing = get_pricing_for_model(model)
except UnknownModelError:
    return Decimal(str(len(steps) * 0.005))  # $0.005 per step fallback
```

### Frontend Error Display

```typescript
{error && (
  <ErrorMessage
    message={error}
    type={error.includes("at least 2") ? "warning" : "error"}
  />
)}

{comparison?.proposals.some(p => p.generation_error) && (
  <WarningMessage>
    Some details unavailable. Showing available information.
  </WarningMessage>
)}
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_comparison_service.py`

- Test common steps detection (identical, partial overlap, no overlap)
- Test cost estimation accuracy (within 50% of expected)
- Test time estimation complexity weighting
- Test edge cases (invalid IDs, single proposal, LLM failures)
- Test caching behavior (cache hit, miss, expiration)

### Integration Tests

**File:** `tests/integration/test_comparison_flow.py`

- End-to-end flow: create session → generate proposals → compare → select
- Verify API response structure
- Test caching avoids regeneration
- Test error responses (404, 400, 500)

### Frontend Tests

**File:** `ProposalComparisonView.test.tsx`

- Show/hide compare button based on proposal count
- Display diff view by default
- Toggle to side-by-side view
- Error message display
- Loading states
- Proposal selection from comparison view

### Test Coverage Target

- Backend: 90%+ coverage
- Frontend: 80%+ coverage
- Integration: Full user flows

---

## Performance Considerations

### Caching Strategy

- Execution graphs cached for 10 minutes
- Cache key: `(session_id, proposal_id)`
- Reduces redundant LLM calls
- Background task expires cache

### Token Cost Impact

- Lightweight analysis: +200 tokens per proposal generation (negligible)
- Full comparison: +1000-2000 tokens (only when requested)
- Net impact: Minimal due to on-demand generation

### Response Time Targets

- Lightweight analysis: <3 seconds (during proposal generation)
- Comparison generation: <5 seconds (first time)
- Cached comparison: <500ms (subsequent requests)

---

## Implementation Timeline

**Total Duration:** 7-10 days

### Phase 1: Backend Foundation (Days 1-3)
- Day 1: Enhanced proposal generation with lightweight analysis
- Day 2: Comparison service with diff logic and estimation
- Day 3: API integration and error handling

**Milestone:** API endpoint functional, testable via Postman

### Phase 2: Frontend Components (Days 4-6)
- Day 4: Core comparison components (DiffComparison, SideBySideComparison)
- Day 5: Interactive features (toggle, selection, API integration)
- Day 6: Integration into PlanView and polish

**Milestone:** Users can compare proposals in UI

### Phase 3: Testing & Polish (Days 7-8)
- Day 7: Unit tests, integration tests, frontend tests
- Day 8: Edge cases, performance optimization, monitoring

**Milestone:** Comprehensive test coverage, robust error handling

### Phase 4: Documentation & Review (Days 9-10)
- Day 9: API documentation, component documentation
- Day 10: Code review, feedback, merge, deploy

**Milestone:** Feature shipped to production

---

## Success Metrics

**Technical Metrics:**
- 90%+ test coverage (backend)
- 80%+ test coverage (frontend)
- Comparison generation <5 seconds (cold cache)
- Comparison generation <500ms (warm cache)
- Cost estimates within 50% of actual costs

**User Metrics:**
- 30%+ of sessions use comparison before proposal selection
- Reduction in proposal re-selection (users commit to first choice more often)
- Positive user feedback on transparency

**Quality Metrics:**
- No regression in existing functionality
- Zero critical bugs in first week post-launch
- Error rate <1% for comparison API

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM analysis unreliable | High | Medium | Add fallbacks, show "estimates" label, track accuracy |
| Step matching too strict/loose | Medium | Medium | Tunable similarity threshold, default 0.85, allow manual override |
| Cost estimates way off | Low | Medium | Show as "estimate", track actuals for model improvement |
| Frontend complexity creep | Medium | High | Reuse existing UI components, keep simple, limit scope |
| Cache invalidation bugs | Medium | Low | 10-minute TTL, manual clear option, extensive testing |

---

## Future Enhancements

### Phase 2 Features
- Export comparison to PDF/Markdown
- Save comparison as snapshot for later reference
- Share comparison link with collaborators
- Historical comparison accuracy tracking

### Integration with Other Features
- **Plan Branching:** Compare branches instead of proposals
- **Interactive Refinement:** Compare refined vs. original plan
- **Cost Optimization:** Highlight cheapest proposal automatically
- **Risk Analysis:** Detailed risk breakdown per step

---

## Related Files

**Backend:**
- `src/planweaver/services/planner.py` - Enhance with lightweight analysis
- `src/planweaver/services/comparison_service.py` - New service
- `src/planweaver/api/routers/sessions.py` - Add comparison endpoint
- `src/planweaver/models/plan.py` - Add ProposalWithAnalysis model
- `tests/test_comparison_service.py` - Unit tests
- `tests/integration/test_comparison_flow.py` - Integration tests

**Frontend:**
- `frontend/src/components/ProposalComparisonView.tsx` - New main component
- `frontend/src/components/DiffComparison.tsx` - Diff view component
- `frontend/src/components/SideBySideComparison.tsx` - Side-by-side component
- `frontend/src/components/PlanView.tsx` - Integrate compare button
- `frontend/src/components/ProposalComparisonView.test.tsx` - Component tests

---

## Approval

**Status:** ✅ Approved
**Date:** 2026-02-26
**Approver:** User
**Next Step:** Invoke writing-plans skill to create detailed implementation plan

---

**End of Design Document**
