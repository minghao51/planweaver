# Plan Optimizer Feature Guide

**Date:** 2026-02-27
**Version:** 1.0.0

## Overview

The Plan Optimizer is an advanced AI-powered feature that generates optimized variants of selected proposals and provides multi-model AI ratings to help users choose the best execution path.

### Key Features

- **AI-Generated Variants:** Automatically creates simplified, enhanced, and cost-optimized versions of proposals
- **Multi-Model Ratings:** Leverages multiple AI models (Claude 3.5 Sonnet, GPT-4o, DeepSeek) to rate plans
- **Interactive Comparison:** Side-by-side comparison of metrics and AI ratings
- **User Feedback:** Allows users to rate and provide feedback on plans

---

## Architecture

### Backend Components

#### Database Models

Located in `src/planweaver/db/models.py`:

1. **OptimizedVariant**
   - Stores AI-generated plan variants
   - Fields: `id`, `session_id`, `proposal_id`, `variant_type`, `execution_graph`, `variant_metadata`, `created_at`
   - Variant types: `simplified`, `enhanced`, `cost-optimized`

2. **PlanRating**
   - Stores AI model ratings for plans
   - Fields: `id`, `session_id`, `plan_id`, `model_name`, `ratings`, `reasoning`, `created_at`
   - Ratings criteria: feasibility, cost_efficiency, time_efficiency, complexity, risk_level

3. **UserRating**
   - Stores user feedback on plans
   - Fields: `id`, `session_id`, `plan_id`, `rating`, `comment`, `rationale`, `created_at`
   - Rating scale: 1-5 stars

#### Services

Located in `src/planweaver/services/`:

1. **VariantGenerator** (`variant_generator.py`)
   - Generates optimized variants using AI
   - Methods:
     - `generate_variant(proposal, variant_type, user_context)`: Creates a single variant
     - `_get_system_prompt(variant_type)`: Returns type-specific prompts
     - `_build_user_prompt(proposal, variant_type, user_context)`: Builds the full prompt

2. **ModelRater** (`model_rater.py`)
   - Rates plans using multiple AI models
   - Methods:
     - `rate_plan(plan, models, criteria)`: Rates a plan with specified models
     - `_rate_with_model(plan, model, criteria)`: Rates with a specific model
     - `_get_rating_system_prompt(criteria)`: Returns rating prompt

3. **OptimizerService** (`optimizer_service.py`)
   - Orchestrates the optimization workflow
   - Methods:
     - `optimize_plan(session_id, selected_proposal_id, ...)`: Main optimization workflow
     - `get_optimization_results(session_id)`: Retrieves results
     - `_generate_and_save_variant(...)`: Generates and persists a variant
     - `_rate_and_save_plans(...)`: Rates and persists ratings

#### API Endpoints

Located in `src/planweaver/api/routers/optimizer.py`:

1. `POST /api/v1/optimizer/optimize`
   - Triggers optimization for a proposal
   - Request: `OptimizerRequest`
   - Response: `OptimizerResponse`

2. `GET /api/v1/optimizer/results/{session_id}`
   - Retrieves optimization results
   - Response: Variants and ratings

3. `POST /api/v1/optimizer/rate`
   - Rates plans with multiple AI models
   - Request: `RatePlansRequest`
   - Response: `RatePlansResponse`

4. `POST /api/v1/optimizer/user-rating`
   - Saves user feedback
   - Request: `UserRatingRequest`
   - Response: `UserRatingResponse`

5. `GET /api/v1/optimizer/state/{session_id}`
   - Gets optimization state
   - Response: `OptimizationStateResponse`

### Frontend Components

#### TypeScript Types

Located in `frontend/src/types/index.ts`:

- `VariantType`: Union of `'simplified' | 'enhanced' | 'cost-optimized'`
- `OptimizedVariant`: Plan variant with metadata
- `ModelRating`: Rating from a single AI model
- `PlanRatings`: Ratings across criteria
- `OptimizerStageData`: Complete stage state

#### Custom Hooks

Located in `frontend/src/hooks/useOptimizer.ts`:

1. **useOptimizer()**
   - Manages optimizer API calls and state
   - Returns: `optimizePlan`, `getOptimizationResults`, `ratePlans`, `saveUserRating`, `getOptimizationState`

2. **useOptimizerStage(sessionId, selectedProposalId)**
   - Manages stage-level state
   - Returns: Variants, ratings, selected plan, status, and setters

#### React Components

Located in `frontend/src/components/optimizer/`:

1. **PlanCard**
   - Displays a single plan with metadata and ratings
   - Props: `id`, `title`, `description`, `variantType`, `metadata`, `ratings`, `averageScore`, `selected`, `onSelect`
   - Features: Selection state, score visualization, variant badge

2. **ComparisonPanel**
   - Side-by-side comparison of multiple plans
   - Props: `plans`, `selectedPlanId`, `onSelectPlan`
   - Features: Metrics table, AI ratings breakdown, selection buttons

3. **OptimizerStage**
   - Main orchestrator component
   - Props: `sessionId`, `selectedProposalId`, `selectedProposalTitle`, `selectedProposalDescription`, `onComplete`, `onBack`
   - Features: Auto-optimization, plan selection, user feedback, loading states

---

## Usage

### User Workflow

1. **Create Session**
   - User provides planning intent
   - System generates strawman proposals

2. **Select Proposal**
   - User reviews proposals
   - Selects a proposal for optimization

3. **Optimizer Stage**
   - System automatically generates variants:
     - **Simplified**: Reduced step count, core functionality only
     - **Enhanced**: Additional quality checks, better reliability
     - **Cost-Optimized**: Uses cheaper models, minimizes cost
   - AI models rate all plans on:
     - Feasibility (1-10)
     - Cost Efficiency (1-10)
     - Time Efficiency (1-10)
     - Complexity (1-10)
     - Risk Level (1-10)

4. **Compare Plans**
   - View side-by-side metrics
   - Compare AI ratings
   - Select best plan

5. **Provide Feedback** (Optional)
   - Rate selected plan (1-5 stars)
   - Add comments
   - Submit to continue

6. **Execute Plan**
   - System proceeds with selected plan
   - Executes optimized or original proposal

### API Usage Examples

#### Trigger Optimization

```bash
curl -X POST http://localhost:8000/api/v1/optimizer/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "selected_proposal_id": "prop-123",
    "optimization_types": ["simplified", "enhanced", "cost-optimized"],
    "user_context": "Prefer cost savings over speed"
  }'
```

#### Get Results

```bash
curl http://localhost:8000/api/v1/optimizer/results/session-123
```

#### Submit User Rating

```bash
curl -X POST http://localhost:8000/api/v1/optimizer/user-rating \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "plan-456",
    "rating": 5,
    "comment": "Excellent optimization",
    "rationale": "Cost-optimized variant saved 40% while maintaining quality"
  }'
```

---

## Configuration

### Environment Variables

No additional environment variables required. Uses existing API settings:

- `GOOGLE_API_KEY` or `GEMINI_API_KEY`: For Gemini models
- `OPENAI_API_KEY`: For GPT models
- `ANTHROPIC_API_KEY`: For Claude models

### Service Configuration

Located in `src/planweaver/services/variant_generator.py`:

```python
# Default models for variant generation
DEFAULT_MODEL = "claude-3.5-sonnet"

# Variant types
VARIANT_TYPES = ["simplified", "enhanced", "cost-optimized"]
```

Located in `src/planweaver/services/model_rater.py`:

```python
# Default models for rating
DEFAULT_MODELS = ["claude-3.5-sonnet", "gpt-4o", "deepseek-chat"]

# Rating criteria
CRITERIA = ["feasibility", "cost_efficiency", "time_efficiency", "complexity", "risk_level"]
```

---

## Testing

### Backend Tests

Run backend tests:

```bash
cd backend
uv run pytest tests/ -v
```

### Frontend Tests

Run frontend tests:

```bash
cd frontend
npm test
```

Run specific optimizer component tests:

```bash
npm test PlanCard
npm test ComparisonPanel
npm test OptimizerStage
```

---

## Troubleshooting

### Common Issues

1. **Optimization Timeout**
   - **Cause:** AI API slow or unresponsive
   - **Solution:** Check API keys, increase timeout in service

2. **No Variants Generated**
   - **Cause:** LLM response parsing failed
   - **Solution:** Check LLM response format, validate JSON structure

3. **Ratings Missing**
   - **Cause:** Model unavailable or API error
   - **Solution:** Check model availability, verify API credentials

4. **Frontend State Not Updating**
   - **Cause:** SSE connection lost
   - **Solution:** Refresh page, check backend logs

### Debug Mode

Enable detailed logging:

```python
# In src/planweaver/services/optimizer_service.py
import logging
logging.getLogger('planweaver.services.optimizer_service').setLevel(logging.DEBUG)
```

---

## Future Enhancements

### Planned Features

1. **Real-Time Streaming**
   - Stream variant generation progress via SSE
   - Show live updates during AI processing

2. **Custom Variant Types**
   - Allow users to define custom optimization strategies
   - Add hybrid variant types

3. **Historical Analysis**
   - Track user preferences over time
   - Suggest variants based on past selections

4. **Collaborative Rating**
   - Aggregate ratings from multiple users
   - Show community scores

5. **Advanced Metrics**
   - Add more rating criteria (security, scalability, maintainability)
   - Provide detailed analysis reports

---

## Contributing

### Adding New Variant Types

1. Update `VariantType` in `frontend/src/types/index.ts`
2. Add prompt in `VariantGenerator._get_system_prompt()`
3. Update documentation

### Adding New Rating Criteria

1. Update `CRITERIA` in `ModelRater`
2. Add criteria to schemas in `frontend/src/api/schemas.py`
3. Update UI components to display new criteria

---

## License

This feature is part of PlanWeaver and follows the same license terms.

## Support

For issues or questions:
- GitHub Issues: [Project Repository]
- Documentation: [Project Wiki]
- Email: [Support Email]
