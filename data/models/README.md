# Model Configuration

PlanWeaver supports multiple AI models for planning and execution tasks. Models can be configured through the database or by editing the YAML configuration files.

## Model Types

- **Planner**: Models optimized for strategic thinking, planning, and breaking down complex tasks
- **Executor**: Models optimized for executing specific tasks and generating outputs

## Available Models

### Gemini (Google)

**Gemini 3.1 Pro (Latest)**
- Best for: Complex planning tasks
- Context: 1-2M tokens
- Type: Planner
- Cost: $2 input/$12 output per 1M tokens

**Gemini 3 Flash**
- Best for: Fast planning and execution
- Context: 1M tokens
- Type: Planner/Executor
- Cost: $0.50 input/$3 output per 1M tokens

**Gemini 3 Pro**
- Best for: Advanced reasoning in execution
- Context: 1M tokens
- Type: Executor
- Cost: $2 input/$12 output per 1M tokens

### Anthropic (Claude)

**Claude 3.5 Sonnet**
- Best for: Coding and technical tasks
- Context: 200K tokens
- Type: Executor
- Cost: $3 input/$15 output per 1M tokens

### OpenAI

**GPT-4o**
- Best for: General purpose tasks
- Context: 128K tokens
- Type: Executor
- Cost: $5 input/$15 output per 1M tokens

### DeepSeek

**DeepSeek Chat**
- Best for: Cost-effective planning
- Context: 128K tokens
- Type: Planner
- Cost: Free

## Adding Custom Models

To add custom models, you have two options:

### Option 1: Edit YAML Configuration

Edit `data/models/default_models.yaml`:

```yaml
models:
  - id: "your-model-id"
    name: "Your Model Name"
    provider: "your-provider"
    type: "planner"  # or "executor"
    is_free: false
    context_length: 128000
    pricing_info:
      input_per_1m: 5.00
      output_per_1m: 15.00
```

Then run:
```bash
uv run python scripts/maintenance/init_models.py
```

### Option 2: Direct Database Insert

```python
from planweaver.db.models import AvailableModel
from planweaver.db.database import get_session

session = get_session()
model = AvailableModel(
    model_id="your-model-id",
    name="Your Model Name",
    provider="your-provider",
    type="planner",
    is_free=False,
    context_length=128000,
    pricing_info={"input_per_1m": 5.0, "output_per_1m": 15.0},
    is_active=True
)
session.add(model)
session.commit()
```

## Updating Models

To update the model list from YAML:

```bash
# Clear existing models and reload from YAML
uv run python scripts/maintenance/init_models.py --clear

# Or add/update without clearing
uv run python scripts/maintenance/init_models.py
```

## Default Models

When the database is empty or unavailable, PlanWeaver falls back to a hardcoded list of models in `src/planweaver/services/llm_gateway.py`. This ensures the app works out-of-the-box even before database initialization.

## Model Selection

Models are selected automatically based on:
1. User preference (if specified)
2. Task type (planning vs execution)
3. Availability and API keys configured

To set API keys, edit your `.env` file:
```bash
GOOGLE_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
OPENROUTER_API_KEY=your_key
```
