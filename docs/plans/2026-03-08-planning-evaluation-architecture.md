# Planning And Evaluation Architecture

**Date:** 2026-03-08
**Status:** Proposed
**Complexity:** High
**Estimated Duration:** 2-4 weeks

## Overview

This design upgrades PlanWeaver from a feature-level planning flow into a **multi-stage planning system** with clear separation between:

1. **Plan synthesis** - Generate candidate plans
2. **Plan normalization** - Convert plans into a common structure
3. **Plan evaluation** - Score and critique plans with separate judge models
4. **Plan comparison** - Rank plans, including manual plans
5. **Outcome learning** - Use execution and human feedback as ground truth

The main goal is to improve planning quality without overloading a single model with conflicting jobs. A model that generates a plan should not be trusted as the only model that rates it.

This design builds on existing PlanWeaver services:

- `Planner` for proposal generation
- `VariantGenerator` for alternative plan generation
- `ModelRater` for evaluation
- `ProposalComparisonService` for comparison
- `OptimizerService` for orchestration

The change is primarily architectural: current capabilities already exist in partial form, but they are not yet organized into a strong pipeline.

## Problem Statement

Current planning capability is strong for proposal generation, but evaluation remains shallow.

### Current Strengths

- Multiple proposals can already be generated
- Plans can already be compared at a lightweight and detailed level
- Plan variants can already be generated
- Multiple models can already rate plans

### Current Gaps

- Generated plans and optimized variants do not share a strict canonical structure
- Rating criteria are too coarse for robust plan judgment
- Rating is mostly absolute scoring, with no pairwise preference judgments
- Manual plans are not first-class inputs to the optimizer pipeline
- No explicit disagreement handling when judge models conflict
- Little feedback from actual execution outcomes flows back into future planning

## Design Goals

### Primary Goals

- Separate plan generation from plan judgment
- Support multiple planner models and multiple judge models
- Compare AI-generated plans against manual plans using the same pipeline
- Produce structured outputs suitable for storage, analysis, and UI comparison
- Learn from execution outcomes and user feedback over time

### Non-Goals

- Full autonomous self-modifying execution during this phase
- Fine-tuning custom models
- Building a full reinforcement learning system
- Replacing existing planning APIs immediately

## Proposed Planning Pipeline

### Stage 1: Plan Synthesis

Generate candidate plans from one or more planner models.

Each candidate should record:

- `source_type`: `llm_generated` or `manual`
- `source_model`: planner model name or `human`
- `planning_style`: `baseline`, `fast`, `risk_averse`, `cost_optimized`, `quality_optimized`
- `prompt_version`
- `raw_plan`

#### Inputs

- User intent
- Locked constraints
- Scenario template
- External context
- Optional user preference profile

#### Outputs

- 2-5 candidate plans in raw form

#### Notes

- Existing `Planner.generate_strawman_proposals()` remains useful for high-level ideation
- Existing `VariantGenerator` should be repositioned as another synthesis source, not only a post-selection optimizer
- Manual plans should enter here as external submissions and continue through the same downstream stages

### Stage 2: Plan Normalization

Convert every generated or manual plan into a shared canonical format.

This is the most important missing layer. Without normalization, judging is inconsistent because different models produce different plan shapes and levels of detail.

#### New Canonical Model

Add a `NormalizedPlan` model to [plan.py](/Users/minghao/Desktop/personal/planweaver/src/planweaver/models/plan.py).

Suggested shape:

```python
class NormalizedPlan(BaseModel):
    id: str
    session_id: str
    source_type: Literal["llm_generated", "manual", "optimized_variant"]
    source_model: str
    planning_style: str
    title: str
    summary: str
    assumptions: List[str]
    constraints: List[str]
    success_criteria: List[str]
    risks: List[str]
    fallbacks: List[str]
    estimated_time_minutes: int | None = None
    estimated_cost_usd: Decimal | None = None
    steps: List["NormalizedStep"]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class NormalizedStep(BaseModel):
    step_id: str
    description: str
    dependencies: List[str] = Field(default_factory=list)
    validation: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    owner_model: str | None = None
    estimated_time_minutes: int | None = None
```

#### Normalization Rules

- Every plan must expose explicit assumptions
- Every plan must expose success criteria
- Every step must state dependencies
- Every plan must include at least one validation or verification path
- Free-text plans that cannot be normalized cleanly should be marked with normalization warnings instead of being discarded

### Stage 3: Plan Evaluation

Judge normalized plans using separate evaluator models.

This replaces today’s mostly flat numeric rating in [model_rater.py](/Users/minghao/Desktop/personal/planweaver/src/planweaver/services/model_rater.py) with a structured rubric.

#### New Evaluation Dimensions

- `completeness`
- `feasibility`
- `constraint_satisfaction`
- `dependency_correctness`
- `risk_coverage`
- `verification_quality`
- `adaptability`
- `cost_realism`
- `time_realism`
- `execution_readiness`

#### Evaluation Output

```python
class PlanEvaluation(BaseModel):
    plan_id: str
    judge_model: str
    rubric_scores: Dict[str, float]
    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    blocking_issues: List[str]
    confidence: float
    verdict: Literal["strong", "acceptable", "weak", "reject"]
```

#### Key Rule

The judge should never see only a title and summary when a normalized plan is available. It must evaluate the full normalized structure.

### Stage 4: Pairwise Comparison

Absolute scoring is useful, but pairwise judgment is often more stable.

For selected plan pairs, ask a judge:

- Which plan is better for this user intent?
- Why?
- Under what assumptions would the weaker plan become preferable?

#### Pairwise Output

```python
class PairwisePlanComparison(BaseModel):
    left_plan_id: str
    right_plan_id: str
    judge_model: str
    winner_plan_id: str
    margin: Literal["narrow", "moderate", "clear"]
    rationale: str
    preference_factors: List[str]
```

#### Why This Matters

- Reduces instability from arbitrary 1-10 scoring scales
- Produces more useful UI explanations
- Works well for comparing AI plans against manual plans

### Stage 5: Meta-Adjudication

Aggregate evaluations across judge models into a final ranking.

This can initially be rule-based rather than model-based.

#### Aggregation Inputs

- Per-judge rubric scores
- Per-judge verdicts
- Pairwise wins/losses
- Normalization warnings
- Manual user preference weights

#### Aggregation Output

```python
class RankedPlanResult(BaseModel):
    plan_id: str
    final_score: float
    rank: int
    confidence: float
    disagreement_level: Literal["low", "medium", "high"]
    recommendation_reason: str
```

#### Disagreement Handling

If judge disagreement is high:

- Do not silently average it away
- Surface the disagreement in API and UI
- Recommend either human review or another targeted comparison pass

### Stage 6: Outcome Learning

Execution results should become the system’s long-term source of truth.

#### Outcome Signals

- Plan selected by user
- Plan executed successfully or failed
- Actual execution duration
- Actual execution cost
- Number of retries
- User feedback after execution
- Manual override frequency

#### Learning Uses

- Re-rank planner models per scenario
- Re-rank judge models per scenario
- Detect plan patterns that correlate with failures
- Improve prompt templates and planning styles

This stage should start as analytics, not autonomous model tuning.

## Manual Plans As First-Class Inputs

Manual plans should be comparable to AI-generated plans without a separate code path.

### Proposed Behavior

Users may submit a manual plan in one of two forms:

- Structured plan JSON
- Free-text plan

The system then:

1. Attempts normalization
2. Records warnings if normalization is incomplete
3. Sends the normalized version through the same evaluator and comparison pipeline
4. Includes the manual plan in final rankings

### Why This Is Important

- Human plans are the most useful baseline for judging whether AI planning is actually improving
- Teams may want to compare “current SOP” against “AI proposal”
- This creates an evaluation dataset over time

## Service Architecture Changes

### New Services

#### `plan_synthesis_service.py`

Responsibilities:

- Generate candidate plans from multiple planner models
- Accept manual plan submissions
- Attach synthesis metadata

#### `plan_normalizer.py`

Responsibilities:

- Convert raw planner output into `NormalizedPlan`
- Normalize manual plans
- Emit warnings and normalization quality scores

#### `plan_evaluator.py`

Responsibilities:

- Replace or absorb `ModelRater`
- Evaluate normalized plans against rubric
- Support multiple judge models

#### `pairwise_comparison_service.py`

Responsibilities:

- Compare plan pairs
- Generate preference explanations
- Support tournament-style ranking when needed

#### `ranking_service.py`

Responsibilities:

- Aggregate absolute and pairwise judgments
- Produce final ranking and confidence

### Existing Services To Refactor

#### [planner.py](/Users/minghao/Desktop/personal/planweaver/src/planweaver/services/planner.py)

- Keep proposal ideation and decomposition responsibilities
- Remove direct ownership of lightweight plan scoring over time
- Focus on generation, not judging

#### [variant_generator.py](/Users/minghao/Desktop/personal/planweaver/src/planweaver/services/variant_generator.py)

- Reposition as a synthesis strategy rather than a pure optimizer stage
- Allow variant generation before final proposal selection if desired

#### [model_rater.py](/Users/minghao/Desktop/personal/planweaver/src/planweaver/services/model_rater.py)

- Replace with `plan_evaluator.py`, or keep as a compatibility wrapper
- Move from shallow numeric ratings to rubric-based structured judgments

#### [comparison_service.py](/Users/minghao/Desktop/personal/planweaver/src/planweaver/services/comparison_service.py)

- Keep execution-graph diffing
- Add integration point for normalized plan comparison and ranking results

#### [optimizer_service.py](/Users/minghao/Desktop/personal/planweaver/src/planweaver/services/optimizer_service.py)

- Evolve into orchestrator for:
  `synthesize -> normalize -> evaluate -> compare -> rank`
- Separate “variant generation” from “evaluation”

## Data Model Changes

### New Models

Add database models for:

- `normalized_plans`
- `plan_evaluations`
- `pairwise_plan_comparisons`
- `ranked_plan_results`
- `plan_outcomes`

### Suggested Tables

#### `normalized_plans`

- `id`
- `session_id`
- `source_type`
- `source_model`
- `planning_style`
- `title`
- `normalized_payload`
- `normalization_warnings`
- `created_at`

#### `plan_evaluations`

- `id`
- `session_id`
- `plan_id`
- `judge_model`
- `rubric_scores`
- `overall_score`
- `strengths`
- `weaknesses`
- `blocking_issues`
- `confidence`
- `verdict`
- `created_at`

#### `pairwise_plan_comparisons`

- `id`
- `session_id`
- `left_plan_id`
- `right_plan_id`
- `judge_model`
- `winner_plan_id`
- `margin`
- `rationale`
- `preference_factors`
- `created_at`

#### `plan_outcomes`

- `id`
- `session_id`
- `plan_id`
- `selected_by_user`
- `executed`
- `execution_status`
- `actual_duration_seconds`
- `actual_cost_usd`
- `retry_count`
- `user_rating`
- `user_feedback`
- `created_at`

## API Changes

### New Endpoints

#### `POST /api/v1/plans/synthesize`

Generate candidate plans from one or more planner models.

#### `POST /api/v1/plans/normalize`

Normalize a raw or manual plan into canonical structure.

#### `POST /api/v1/plans/evaluate`

Evaluate one or more normalized plans with one or more judge models.

#### `POST /api/v1/plans/compare`

Run pairwise or grouped comparison between candidate plans.

#### `POST /api/v1/plans/rank`

Return final plan ranking with confidence and disagreement metadata.

#### `POST /api/v1/plans/manual`

Submit a manual plan for normalization and comparison.

#### `POST /api/v1/plans/outcomes`

Record post-selection or post-execution outcome data.

### Backward Compatibility

Existing optimizer endpoints can remain while internally delegating to the new pipeline.

This keeps the frontend working during migration while reducing implementation risk.

## UI Implications

### New Capabilities

- Show planner source and planning style for each candidate
- Show normalization warnings for manual or low-quality plans
- Display rubric scores, not just a single blended number
- Show judge disagreement explicitly
- Compare AI-generated plans and manual plans side-by-side
- Explain why a plan ranked first

### Suggested UI Flow

1. User submits intent
2. System generates candidate plans
3. User optionally adds a manual plan
4. System normalizes all plans
5. System evaluates and ranks
6. UI shows:
   - ranked plans
   - score breakdown
   - disagreement indicators
   - pairwise explanations
7. User selects a plan
8. Execution outcome is recorded after completion

## Evaluation Strategy

This project should measure planning quality with more than unit tests.

### Add An `evals/` Dataset

Store a small but representative evaluation set:

- task prompt
- constraints
- optional manual reference plan
- expected plan traits
- known failure patterns

Suggested scenarios:

- code refactoring
- market analysis
- blog generation
- data analysis
- ambiguous requests requiring clarification

### Metrics To Track

- Judge agreement rate
- Pairwise ranking consistency
- Human-vs-AI preference rate
- Execution success rate by planner model
- Execution success rate by planning style
- Correlation between judge score and execution success

## Implementation Phases

### Phase 1: Canonical Structure

- Add `NormalizedPlan` and related Pydantic models
- Implement `plan_normalizer.py`
- Support manual plan ingestion
- Add database persistence for normalized plans

### Phase 2: Stronger Evaluation

- Replace `ModelRater` with rubric-based structured evaluator
- Add pairwise comparison support
- Add ranking service with disagreement handling

### Phase 3: Pipeline Integration

- Refactor optimizer workflow to use the full pipeline
- Preserve current API behavior through compatibility wrappers
- Update frontend comparison views

### Phase 4: Outcome Learning

- Record execution outcomes
- Add dashboards or reports for planner/judge effectiveness
- Use analytics to adjust default planner and judge choices

## Risks And Trade-Offs

### Increased Cost And Latency

Using multiple planner and judge models will increase cost and response time.

Mitigations:

- Use cheaper models for normalization and lightweight passes
- Limit full judge evaluation to top candidate plans
- Cache normalized plans and evaluations

### Overfitting To Judge Models

Plans may start optimizing for what judge models prefer rather than what executes well.

Mitigations:

- Track outcome metrics separately
- Use real execution success as the long-term calibration target
- Compare judge preference against human and execution outcomes

### UI Complexity

More scores and more metadata can make selection harder rather than easier.

Mitigations:

- Keep default UI opinionated
- Show a recommended plan first
- Make advanced judge details expandable

## Success Criteria

This design is successful when:

- Manual and AI-generated plans can be evaluated in the same pipeline
- Final rankings expose confidence and disagreement
- Judge outputs are more actionable than today’s flat scores
- Better-ranked plans correlate more strongly with successful execution
- Teams can use manual plans as baselines to measure AI planning progress

## Recommended First Slice

The highest-value first implementation slice is:

1. Add `NormalizedPlan`
2. Add manual plan ingestion
3. Replace flat ratings with rubric-based evaluation
4. Add pairwise comparison for top 2-3 plans

This delivers the core architecture without waiting for the full outcome-learning loop.
