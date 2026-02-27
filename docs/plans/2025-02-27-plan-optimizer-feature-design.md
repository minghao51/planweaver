# Plan Optimizer & Multi-Model Rating Feature Design

**Date:** 2025-02-27
**Status:** Design Approved
**Author:** Claude + User
**Target Audience:** Developers, Business Stakeholders, End Users

## Overview

Add a new "Plan Optimizer" stage to the existing workflow that generates AI-improved variants of selected proposals and provides multi-model AI ratings to help users choose the best execution path. This feature sits between proposal selection and execution, enabling users to optimize their chosen plan before committing resources.

## Goals

1. **Demonstrate Technical Sophistication:** Showcase multi-model AI orchestration, real-time updates, and intelligent plan analysis
2. **Enhance User Experience:** Provide data-driven decision-making tools with beautiful visualizations
3. **Deliver Business Value:** Enable cost and time optimization before execution
4. **Support Multiple Audiences:** Appeal to developers (architecture), stakeholders (value), and users (usability)

## Proposed Solution: Approach 1 - Plan Optimizer

### User Flow

```
Intent → Questions → Proposals → Select Proposal →
[NEW: Optimize Stage → Generate Variants → Multi-Model Rating → Compare & Finalize] →
Execute → Results
```

### Optimizer Stage Workflow

1. User selects a proposal from the initial 3 strawman proposals
2. "Optimize Plan" button appears with subtitle "Get AI-generated improvements and compare ratings"
3. User clicks "Optimize" → enters OptimizerStage
4. Backend generates 2-3 optimized variants:
   - **Simplified:** Removes optional steps, merges parallel tasks (30-40% fewer steps)
   - **Enhanced:** Adds validation, error handling, rollback mechanisms
   - **Cost-optimized:** Uses cheaper models, reduces token usage (30-50% cost savings)
5. Backend triggers multi-model rating (3 AI models rate each plan on 4 criteria)
6. Frontend displays comparison view with table, radar chart, and detailed ratings
7. User reviews, adds their own rating/comments, selects best plan
8. User clicks "Execute with [Plan Name]" → proceeds to execution

## UI/UX Design

### Layout Structure

**Split-screen view:**
- **Left panel:** Selected proposal + optimized variants (plan cards with execution graphs)
- **Right panel:** Comparison tools (table, radar chart, AI model ratings, user rating input)

### Key Components

1. **OptimizerStage.tsx** - Main container coordinating the optimization workflow
2. **PlanCardsPanel** - Shows original + variants in expandable cards with execution graphs
3. **ComparisonPanel** - Tabbed view (Table | Radar Chart | Side-by-Side)
4. **ModelRatingsDisplay** - Accordion showing ratings from Claude, GPT-4o, DeepSeek
5. **UserRatingControl** - 5-star rating with comment input
6. **RadarChart.tsx** - 3-axis visualization (Cost, Speed, Feasibility)

### Visual Design

- **Color coding:** Original (blue), Simplified (green), Enhanced (purple), Selected (gold)
- **Loading states:** Progress bars showing variant generation and rating progress
- **Micro-interactions:** Smooth animations, hover effects, pulse on "Optimize" button

### Demo Highlights

- "Compare All" button for side-by-side view (wow factor)
- "Model Consensus" indicator (agree vs disagree)
- "Your Savings" badge showing cost/time improvements
- Export comparison as PDF for stakeholders

## Backend Architecture

### New API Endpoints

```http
POST /api/v1/sessions/{session_id}/optimize
# Generate optimized variants of selected proposal

POST /api/v1/sessions/{session_id}/rate
# Rate all plans (original + variants) with multiple AI models

POST /api/v1/sessions/{session_id}/user-rating
# Save user's rating and comments

GET /api/v1/sessions/{session_id}/optimization-state
# Poll optimization progress (or use SSE)
```

### New Services

1. **OptimizerService** - Generates optimized variants using different strategies
2. **ModelRater** - Coordinates multi-model rating requests in parallel
3. **VariantGenerator** - Creates simplified, enhanced, cost-optimized versions

### Database Schema

```sql
CREATE TABLE optimized_variants (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    proposal_id UUID REFERENCES proposals(id),
    variant_type VARCHAR(50),
    execution_graph JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE plan_ratings (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    plan_id UUID,
    model_name VARCHAR(100),
    ratings JSONB,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_ratings (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    plan_id UUID,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    rationale TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Real-time Updates (SSE)

New SSE events:
- `variant_generated` - Emitted when each variant is ready
- `model_rated` - Emitted when a model completes rating
- `ratings_complete` - All models finished rating

## Data Models

### TypeScript Types

```typescript
type VariantType = 'simplified' | 'enhanced' | 'cost-optimized';

interface OptimizedVariant {
  id: string;
  type: VariantType;
  name: string;
  description: string;
  executionGraph: ExecutionGraph;
  steps: ExecutionStep[];
  metadata: {
    stepCount: number;
    complexityScore: number;
    optimizationNotes: string;
    estimatedCost: number;
    estimatedTime: number;
  };
}

interface ModelRating {
  modelName: string;
  feasibility: number; // 1-10
  costEfficiency: number;
  timeEfficiency: number;
  complexity: number;
  overallScore: number;
  reasoning: string;
}

interface OptimizerState {
  status: 'idle' | 'generating_variants' | 'rating' | 'completed' | 'error';
  selectedProposalId: string;
  variants: OptimizedVariant[];
  ratings: PlanRatings[];
  userRating?: UserRating;
  executionChoice?: string;
  progress: { variantsGenerated, variantsTotal, ratingsCompleted, ratingsTotal };
  error?: string;
}
```

### State Management

- **useOptimizer** hook - Manages optimizer state, API calls, and error handling
- **useOptimizerSSE** hook - Listens for real-time optimization events
- Session storage for demo resilience (restore state on refresh)

## Technical Implementation

### Component Architecture

```
OptimizerStage
├── OptimizerHeader
├── OptimizerContent
│   ├── PlanCardsPanel (left)
│   │   ├── OriginalProposalCard
│   │   └── VariantCard (x2-3)
│   └── ComparisonPanel (right)
│       ├── ComparisonTable
│       ├── RadarChart
│       └── ModelRatingsDisplay
└── OptimizerFooter
```

### Performance Optimizations

- **Frontend:** Code splitting, memoization, virtual scrolling (if many variants)
- **Backend:** Parallel API calls to models, prompt caching, streaming responses

### Error Handling

- **Frontend:** Error boundary with retry options, graceful degradation (continue with partial ratings)
- **Backend:** Automatic retry with exponential backoff, fallback to simplified variant, switch to backup model on rate limits

### Security & Validation

- Input validation (proposal ID format, rating range 1-5)
- Rate limiting (10 optimization requests per minute per user)
- Daily quota checks to prevent abuse

## Testing Strategy

### Frontend Tests

- Component tests for OptimizerStage, PlanCard, ComparisonPanel
- Hook tests for useOptimizer, useOptimizerSSE
- User interaction flows (select plan, rate, execute)

### Backend Tests

- Service tests for variant generation, multi-model rating
- Error handling tests (timeouts, rate limits, model failures)
- Performance tests (parallel API calls, caching effectiveness)

## Demo Support

### Mock Data

Pre-loaded demo data for offline presentations:
- 3 variants with different profiles
- Complete multi-model ratings
- User-rated example

### Demo Mode Toggle

```typescript
const [demoMode, setDemoMode] = useState(false);
if (demoMode) {
  return <OptimizerStage data={mockOptimizerData} demoMode />;
}
```

## Performance Targets

- **Generate variants:** 5-10 seconds
- **Rate plans:** 15-30 seconds (3 plans × 3 models, parallelized)
- **Total optimization:** <45 seconds (demo-friendly)

## Success Metrics

- **Technical:** Multi-model orchestration works seamlessly, SSE provides real-time updates
- **UX:** Users can understand comparison and confidently choose a plan
- **Business:** Demonstrated cost/time savings (e.g., "This variant saves $0.70 and 3 minutes")
- **Demo:** Clear narrative flow from planning → optimization → execution

## Migration Path

1. Add new database tables
2. Implement backend services (OptimizerService, ModelRater)
3. Add API routes with SSE support
4. Build frontend components and hooks
5. Integrate into existing PlanView workflow
6. Add comprehensive tests
7. Create demo mode with mock data
8. User acceptance testing

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM API costs for rating | Use cheaper models for ratings, cache results, implement rate limits |
| Slow rating delays user | Show progress via SSE, allow proceeding with partial ratings |
| Models disagree significantly | Show consensus indicator, explain disagreement as "diverse perspectives" |
| UI complexity overwhelms users | Progressive disclosure (basic view by default, advanced on click) |

## Future Enhancements

- Learn from user ratings to improve proposal generation
- A/B test which optimization strategies users prefer
- Add more optimization types (security-focused, speed-focused)
- Export plans to other formats (Markdown, JSON)
- Collaborative rating (multiple team members rate and discuss)

## References

- Existing PlanView component structure
- SSE implementation in current codebase
- ReactFlow for execution graph visualization
- Multi-model routing architecture
