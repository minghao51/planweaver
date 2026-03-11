# Plan Optimizer & Multi-Model Rating Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an "Optimize Stage" between proposal selection and execution that generates AI-improved plan variants and provides multi-model AI ratings to help users choose the best execution path.

**Architecture:**
- Frontend: New OptimizerStage component with split-screen layout (plans left, comparison right), custom hooks for state management and SSE
- Backend: New OptimizerService and ModelRater services, new database tables for variants/ratings, REST API endpoints with SSE streaming
- Integration: Insert new stage into existing PlanView workflow after proposal selection

**Tech Stack:**
- Frontend: React 18, TypeScript, ReactFlow (execution graphs), Lucide React (icons)
- Backend: Python, FastAPI, SQLAlchemy, Pydantic
- AI: Multi-model orchestration (Claude 3.5 Sonnet, GPT-4o, DeepSeek V3)
- Real-time: Server-Sent Events (SSE)

---

## Task 1: Database Schema Creation

**Files:**
- Create: `backend/migrations/versions/2025_02_27_add_optimizer_tables.py`
- Reference: `backend/models/session.py` (existing structure)

**Step 1: Create Alembic migration for new tables**

Create `backend/migrations/versions/2025_02_27_add_optimizer_tables.py`:

```python
"""add optimizer tables

Revision ID: 2025_02_27_optimizer
Revises: <latest_revision_id>
Create Date: 2025-02-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '2025_02_27_optimizer'
down_revision = '<latest_revision_id>'  # Update with actual latest revision
branch_labels = None
depends_on = None


def upgrade():
    # Optimized variants table
    op.create_table(
        'optimized_variants',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('proposal_id', sa.UUID(), nullable=False),
        sa.Column('variant_type', sa.String(50), nullable=False),
        sa.Column('execution_graph', JSONB(), nullable=False),
        sa.Column('metadata', JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_optimized_variants_session_id', 'optimized_variants', ['session_id'], unique=False)
    op.create_index('ix_optimized_variants_proposal_id', 'optimized_variants', ['proposal_id'], unique=False)

    # Plan ratings table
    op.create_table(
        'plan_ratings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('plan_id', sa.UUID(), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('ratings', JSONB(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_plan_ratings_session_id', 'plan_ratings', ['session_id'], unique=False)
    op.create_index('ix_plan_ratings_plan_id', 'plan_ratings', ['plan_id'], unique=False)
    op.create_index('ix_plan_ratings_model_name', 'plan_ratings', ['model_name'], unique=False)

    # User ratings table
    op.create_table(
        'user_ratings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('plan_id', sa.UUID(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_ratings_session_id', 'user_ratings', ['session_id'], unique=False)
    op.create_index('ix_user_ratings_plan_id', 'user_ratings', ['plan_id'], unique=False)


def downgrade():
    op.drop_index('ix_user_ratings_plan_id', table_name='user_ratings')
    op.drop_index('ix_user_ratings_session_id', table_name='user_ratings')
    op.drop_table('user_ratings')

    op.drop_index('ix_plan_ratings_model_name', table_name='plan_ratings')
    op.drop_index('ix_plan_ratings_plan_id', table_name='plan_ratings')
    op.drop_index('ix_plan_ratings_session_id', table_name='plan_ratings')
    op.drop_table('plan_ratings')

    op.drop_index('ix_optimized_variants_proposal_id', table_name='optimized_variants')
    op.drop_index('ix_optimized_variants_session_id', table_name='optimized_variants')
    op.drop_table('optimized_variants')
```

**Step 2: Run migration**

Run: `cd backend && uv run alembic upgrade head`
Expected: SUCCESS, 3 new tables created

**Step 3: Verify tables exist**

Run: `cd backend && uv run python -c "from backend.database import engine; import sqlalchemy; inspector = sqlalchemy.inspect(engine); print(inspector.get_table_names())"`
Expected: List includes 'optimized_variants', 'plan_ratings', 'user_ratings'

**Step 4: Commit**

```bash
git add backend/migrations/versions/2025_02_27_add_optimizer_tables.py
git commit -m "feat(db): add optimizer tables for variants and ratings"
```

---

## Task 2: Backend Models - SQLAlchemy Models

**Files:**
- Create: `backend/models/optimized_variant.py`
- Create: `backend/models/plan_rating.py`
- Create: `backend/models/user_rating.py`
- Reference: `backend/models/session.py` (for existing patterns)

**Step 1: Create OptimizedVariant model**

Create `backend/models/optimized_variant.py`:

```python
from datetime import datetime
from sqlalchemy import Column, String, UUID, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from backend.database import Base
import uuid


class OptimizedVariant(Base):
    __tablename__ = "optimized_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True)
    proposal_id = Column(UUID(as_uuid=True), ForeignKey("proposals.id"), nullable=False, index=True)
    variant_type = Column(String(50), nullable=False)  # 'simplified', 'enhanced', 'cost-optimized'
    execution_graph = Column(JSONB, nullable=False)
    metadata = Column(JSONB, nullable=True)  # {step_count, complexity_score, optimization_notes, etc}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="optimized_variants")
    proposal = relationship("Proposal", back_populates="optimized_variants")
    ratings = relationship("PlanRating", back_populates="variant", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "proposal_id": str(self.proposal_id),
            "variant_type": self.variant_type,
            "execution_graph": self.execution_graph,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
```

**Step 2: Create PlanRating model**

Create `backend/models/plan_rating.py`:

```python
from datetime import datetime
from sqlalchemy import Column, String, UUID, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from backend.database import Base
import uuid


class PlanRating(Base):
    __tablename__ = "plan_ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Can be proposal or variant ID
    model_name = Column(String(100), nullable=False, index=True)  # 'claude-3.5-sonnet', 'gpt-4o', etc
    ratings = Column(JSONB, nullable=False)  # {feasibility: 8.5, cost_efficiency: 7.0, ...}
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="plan_ratings")

    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "plan_id": str(self.plan_id),
            "model_name": self.model_name,
            "ratings": self.ratings,
            "reasoning": self.reasoning,
            "created_at": self.created_at.isoformat(),
        }
```

**Step 3: Create UserRating model**

Create `backend/models/user_rating.py`:

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, UUID, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base
import uuid


class UserRating(Base):
    __tablename__ = "user_ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="user_ratings")

    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "plan_id": str(self.plan_id),
            "rating": self.rating,
            "comment": self.comment,
            "rationale": self.rationale,
            "created_at": self.created_at.isoformat(),
        }
```

**Step 4: Update Session model to include relationships**

Open `backend/models/session.py`, add to Session class:

```python
# Add these relationships after existing ones
optimized_variants = relationship("OptimizedVariant", back_populates="session", cascade="all, delete-orphan")
plan_ratings = relationship("PlanRating", back_populates="session", cascade="all, delete-orphan")
user_ratings = relationship("UserRating", back_populates="session", cascade="all, delete-orphan")
```

**Step 5: Update Proposal model**

Open `backend/models/proposal.py`, add to Proposal class:

```python
optimized_variants = relationship("OptimizedVariant", back_populates="proposal", cascade="all, delete-orphan")
```

**Step 6: Update model imports**

Open `backend/models/__init__.py`, add:

```python
from backend.models.optimized_variant import OptimizedVariant
from backend.models.plan_rating import PlanRating
from backend.models.user_rating import UserRating
```

**Step 7: Write test for models**

Create `backend/tests/models/test_optimizer_models.py`:

```python
import pytest
from backend.models.optimized_variant import OptimizedVariant
from backend.models.plan_rating import PlanRating
from backend.models.user_rating import UserRating
from backend.database import Session


def test_create_optimized_variant(db_session):
    variant = OptimizedVariant(
        session_id=uuid.uuid4(),
        proposal_id=uuid.uuid4(),
        variant_type="simplified",
        execution_graph={"nodes": [], "edges": []},
        metadata={"step_count": 5}
    )
    db_session.add(variant)
    db_session.commit()

    assert variant.id is not None
    assert variant.variant_type == "simplified"
    assert variant.to_dict()["variant_type"] == "simplified"


def test_create_plan_rating(db_session):
    rating = PlanRating(
        session_id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        model_name="claude-3.5-sonnet",
        ratings={"feasibility": 8.5, "cost_efficiency": 7.0},
        reasoning="Good plan"
    )
    db_session.add(rating)
    db_session.commit()

    assert rating.id is not None
    assert rating.model_name == "claude-3.5-sonnet"


def test_user_rating_constraint(db_session):
    """Test that rating must be between 1 and 5"""
    with pytest.raises(Exception):  # Integrity error from DB constraint
        rating = UserRating(
            session_id=uuid.uuid4(),
            plan_id=uuid.uuid4(),
            rating=6  # Invalid
        )
        db_session.add(rating)
        db_session.commit()
```

**Step 8: Run tests**

Run: `cd backend && uv run pytest backend/tests/models/test_optimizer_models.py -v`
Expected: All tests PASS

**Step 9: Commit**

```bash
git add backend/models/
git commit -m "feat(models): add OptimizedVariant, PlanRating, UserRating models"
```

---

## Task 3: Pydantic Schemas for API

**Files:**
- Create: `backend/schemas/optimizer.py`
- Reference: `backend/schemas/session.py` (for existing patterns)

**Step 1: Write failing tests for schemas**

Create `backend/tests/schemas/test_optimizer_schemas.py`:

```python
import pytest
from pydantic import ValidationError
from backend.schemas.optimizer import (
    OptimizerRequest,
    OptimizerResponse,
    RatePlansRequest,
    RatePlansResponse,
    UserRatingRequest
)


def test_optimizer_request_valid():
    request = OptimizerRequest(
        selected_proposal_id="prop-123",
        optimization_types=["simplified", "enhanced"]
    )
    assert request.selected_proposal_id == "prop-123"
    assert len(request.optimization_types) == 2


def test_optimizer_request_invalid_proposal_id():
    with pytest.raises(ValidationError):
        OptimizerRequest(
            selected_proposal_id="short",  # Too short
            optimization_types=["simplified"]
        )


def test_optimizer_request_invalid_type():
    with pytest.raises(ValidationError):
        OptimizerRequest(
            selected_proposal_id="prop-123",
            optimization_types=["invalid_type"]  # Not valid
        )


def test_user_rating_invalid_range():
    with pytest.raises(ValidationError):
        UserRatingRequest(
            plan_id="plan-123",
            rating=6  # Must be 1-5
        )
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest backend/tests/schemas/test_optimizer_schemas.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.schemas.optimizer'"

**Step 3: Implement schemas**

Create `backend/schemas/optimizer.py`:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Literal


class OptimizerRequest(BaseModel):
    selected_proposal_id: str = Field(..., min_length=10)
    optimization_types: List[Literal["simplified", "enhanced", "cost-optimized"]] = Field(
        default=["simplified", "enhanced"]
    )

    @validator("optimization_types")
    def validate_types(cls, v):
        valid_types = {"simplified", "enhanced", "cost-optimized"}
        if not set(v).issubset(valid_types):
            raise ValueError(f"Invalid types. Must be one of: {valid_types}")
        return v


class OptimizedVariantSchema(BaseModel):
    id: str
    type: Literal["simplified", "enhanced", "cost-optimized"]
    name: str
    description: str
    execution_graph: Dict
    steps: List[Dict]
    metadata: Dict


class OptimizerResponse(BaseModel):
    optimization_id: str
    status: Literal["completed", "partial", "failed"]
    variants: List[OptimizedVariantSchema]


class RatePlansRequest(BaseModel):
    plan_ids: List[str] = Field(..., min_items=1)
    models: List[str] = Field(default=["claude-3.5-sonnet", "gpt-4o", "deepseek-v3"])
    criteria: List[str] = Field(
        default=["feasibility", "cost_efficiency", "time_efficiency", "complexity"]
    )


class ModelRatingSchema(BaseModel):
    model_name: str
    feasibility: float = Field(..., ge=1.0, le=10.0)
    cost_efficiency: float = Field(..., ge=1.0, le=10.0)
    time_efficiency: float = Field(..., ge=1.0, le=10.0)
    complexity: float = Field(..., ge=1.0, le=10.0)
    overall_score: float
    reasoning: str


class PlanRatingsSchema(BaseModel):
    plan_id: str
    ratings: Dict[str, ModelRatingSchema]
    average_score: float


class RatePlansResponse(BaseModel):
    rating_id: str
    status: Literal["completed", "partial", "failed"]
    ratings: Dict[str, PlanRatingsSchema]


class UserRatingRequest(BaseModel):
    plan_id: str = Field(..., min_length=10)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    rationale: Optional[str] = None


class UserRatingResponse(BaseModel):
    saved: bool
    rating_id: str


class OptimizationStateResponse(BaseModel):
    status: Literal["idle", "generating_variants", "rating", "completed", "error"]
    phase: Optional[str] = None
    progress: Dict[str, int]
    eta_seconds: Optional[int] = None
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest backend/tests/schemas/test_optimizer_schemas.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/schemas/optimizer.py backend/tests/schemas/test_optimizer_schemas.py
git commit -m "feat(schemas): add optimizer API request/response schemas"
```

---

## Task 4: Backend Service - Variant Generator

**Files:**
- Create: `backend/services/variant_generator.py`
- Create: `backend/tests/services/test_variant_generator.py`
- Create: `backend/prompts/optimization_prompts.py`

**Step 1: Create optimization prompts**

Create `backend/prompts/optimization_prompts.py`:

```python
OPTIMIZATION_STRATEGIES = {
    "simplified": {
        "name": "Simplified Plan",
        "prompt": """You are a plan optimization expert. Your task is to SIMPLIFY the following execution plan by:
1. Merging parallel steps that can be done together
2. Removing optional validation steps
3. Combining redundant tasks
4. Eliminating dependencies that aren't strictly necessary

GOAL: Reduce step count by 30-40% while maintaining core functionality.

ORIGINAL PLAN:
{plan_description}

EXECUTION GRAPH:
{execution_graph}

Provide your optimized plan as JSON:
{{
  "name": "Simplified Plan",
  "description": "Streamlined execution with merged steps",
  "execution_graph": {{...}},  // Optimized graph structure
  "steps": [
    {{
      "id": "step_1",
      "description": "...",
      "model": "model-name",
      "dependencies": []
    }}
  ],
  "optimization_notes": "Merged steps X and Y, removed optional validation Z"
}}""",
        "focus": "Reduce complexity and step count"
    },
    "enhanced": {
        "name": "Enhanced Plan",
        "prompt": """You are a plan optimization expert. Your task is to ENHANCE the following execution plan by:
1. Adding validation checkpoints at critical stages
2. Including error handling and rollback mechanisms
3. Adding quality assurance steps
4. Including monitoring and logging

GOAL: Increase reliability, robustness, and error resilience.

ORIGINAL PLAN:
{plan_description}

EXECUTION GRAPH:
{execution_graph}

Provide your enhanced plan as JSON:
{{
  "name": "Enhanced Plan",
  "description": "Robust execution with validation and error handling",
  "execution_graph": {{...}},
  "steps": [
    {{
      "id": "step_1",
      "description": "...",
      "model": "model-name",
      "dependencies": [],
      "validation": "..."
    }}
  ],
  "optimization_notes": "Added validation after step 3, rollback mechanism for step 5"
}}""",
        "focus": "Increase reliability and robustness"
    },
    "cost-optimized": {
        "name": "Cost-Optimized Plan",
        "prompt": """You are a plan optimization expert. Your task is to OPTIMIZE FOR COST by:
1. Using more cost-effective models where appropriate (e.g., deepseek instead of claude)
2. Reducing token usage through concise prompts
3. Batching operations where possible
4. Eliminating non-essential LLM calls

GOAL: Reduce estimated cost by 30-50% while maintaining quality.

ORIGINAL PLAN:
{plan_description}

EXECUTION GRAPH:
{execution_graph}

Provide your cost-optimized plan as JSON:
{{
  "name": "Cost-Optimized Plan",
  "description": "Budget-friendly execution with optimized model selection",
  "execution_graph": {{...}},
  "steps": [
    {{
      "id": "step_1",
      "description": "...",
      "model": "deepseek-v3",  // Cheaper model
      "dependencies": []
    }}
  ],
  "optimization_notes": "Switched to deepseek for steps 1-3, batched operations"
}}""",
        "focus": "Reduce execution cost"
    }
}
```

**Step 2: Write test for variant generator**

Create `backend/tests/services/test_variant_generator.py`:

```python
import pytest
from backend.services.variant_generator import VariantGenerator
from backend.models.proposal import Proposal


@pytest.mark.asyncio
async def test_generate_simplified_variant():
    generator = VariantGenerator()

    proposal = Proposal(
        id="prop-123",
        session_id="session-123",
        execution_graph={"nodes": [{"id": "1"}, {"id": "2"}], "edges": []},
        steps=[
            {"id": "1", "description": "Step 1", "model": "claude-3.5-sonnet"},
            {"id": "2", "description": "Step 2", "model": "claude-3.5-sonnet"}
        ]
    )

    variant = await generator.generate_variant(proposal, "simplified")

    assert variant.type == "simplified"
    assert variant.metadata["step_count"] <= len(proposal.steps)
    assert "optimization_notes" in variant.metadata


@pytest.mark.asyncio
async def test_generate_all_variant_types():
    generator = VariantGenerator()
    proposal = create_mock_proposal()

    variants = await generator.generate_variants(
        proposal,
        types=["simplified", "enhanced", "cost-optimized"]
    )

    assert len(variants) == 3
    types = [v.type for v in variants]
    assert "simplified" in types
    assert "enhanced" in types
    assert "cost-optimized" in types
```

**Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest backend/tests/services/test_variant_generator.py::test_generate_simplified_variant -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.services.variant_generator'"

**Step 4: Implement VariantGenerator service**

Create `backend/services/variant_generator.py`:

```python
import asyncio
import json
from typing import List
from backend.models.proposal import Proposal
from backend.models.optimized_variant import OptimizedVariant
from backend.prompts.optimization_prompts import OPTIMIZATION_STRATEGIES
from backend.services.llm_service import LLMService  # Existing service


class VariantGenerator:
    def __init__(self):
        self.llm_service = LLMService()

    async def generate_variants(
        self,
        proposal: Proposal,
        types: List[str] = None
    ) -> List[OptimizedVariant]:
        """Generate multiple optimized variants of a proposal"""
        if types is None:
            types = ["simplified", "enhanced", "cost-optimized"]

        tasks = [self.generate_variant(proposal, variant_type) for variant_type in types]
        variants = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failed generations
        successful_variants = [v for v in variants if isinstance(v, OptimizedVariant)]

        return successful_variants

    async def generate_variant(
        self,
        proposal: Proposal,
        variant_type: str
    ) -> OptimizedVariant:
        """Generate a single optimized variant"""
        if variant_type not in OPTIMIZATION_STRATEGIES:
            raise ValueError(f"Unknown variant type: {variant_type}")

        strategy = OPTIMIZATION_STRATEGIES[variant_type]

        # Format prompt with plan details
        prompt = strategy["prompt"].format(
            plan_description=self._describe_plan(proposal),
            execution_graph=json.dumps(proposal.execution_graph, indent=2)
        )

        # Call LLM to generate optimized variant
        response = await self.llm_service.complete(
            prompt=prompt,
            model="claude-3.5-sonnet",  # Use high-quality model for generation
            response_format="json"
        )

        # Parse response
        variant_data = json.loads(response)

        # Create OptimizedVariant instance
        variant = OptimizedVariant(
            session_id=proposal.session_id,
            proposal_id=proposal.id,
            variant_type=variant_type,
            execution_graph=variant_data["execution_graph"],
            steps=variant_data["steps"],
            metadata={
                "step_count": len(variant_data["steps"]),
                "complexity_score": self._calculate_complexity(variant_data["steps"]),
                "optimization_notes": variant_data["optimization_notes"],
                "estimated_cost": self._estimate_cost(variant_data["steps"]),
                "estimated_time": self._estimate_time(variant_data["steps"])
            }
        )

        return variant

    def _describe_plan(self, proposal: Proposal) -> str:
        """Generate a text description of the plan"""
        step_desc = "\n".join([
            f"- {step['description']}" for step in proposal.steps
        ])
        return f"Plan with {len(proposal.steps)} steps:\n{step_desc}"

    def _calculate_complexity(self, steps: List) -> float:
        """Calculate complexity score based on step count and dependencies"""
        dep_count = sum(len(s.get("dependencies", [])) for s in steps)
        return round(len(steps) * 0.5 + dep_count * 0.3, 2)

    def _estimate_cost(self, steps: List) -> float:
        """Estimate cost based on models used"""
        model_costs = {
            "claude-3.5-sonnet": 0.50,
            "gpt-4o": 0.60,
            "deepseek-v3": 0.30
        }
        return sum(model_costs.get(s.get("model", "claude-3.5-sonnet"), 0.50) for s in steps)

    def _estimate_time(self, steps: List) -> int:
        """Estimate execution time in minutes"""
        return len(steps) * 3  # Assume 3 minutes per step
```

**Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest backend/tests/services/test_variant_generator.py -v`
Expected: All tests PASS (may need to mock LLM service)

**Step 6: Commit**

```bash
git add backend/services/variant_generator.py backend/prompts/optimization_prompts.py backend/tests/services/test_variant_generator.py
git commit -m "feat(service): add VariantGenerator service for creating optimized plan variants"
```

---

## Task 5: Backend Service - Model Rater

**Files:**
- Create: `backend/services/model_rater.py`
- Create: `backend/tests/services/test_model_rater.py`

**Step 1: Write test for model rater**

Create `backend/tests/services/test_model_rater.py`:

```python
import pytest
from backend.services.model_rater import ModelRater


@pytest.mark.asyncio
async def test_rate_single_plan():
    rater = ModelRater()

    plan = {
        "id": "plan-123",
        "execution_graph": {"nodes": [{"id": "1"}], "edges": []},
        "steps": [{"description": "Test step"}]
    }

    ratings = await rater.rate_single_plan(
        plan=plan,
        model="claude-3.5-sonnet",
        criteria=["feasibility", "cost_efficiency"]
    )

    assert "feasibility" in ratings
    assert "cost_efficiency" in ratings
    assert 1 <= ratings["feasibility"] <= 10
    assert "reasoning" in ratings


@pytest.mark.asyncio
async def test_multi_model_rating():
    rater = ModelRater()

    plans = [
        {"id": "plan-1", "execution_graph": {}, "steps": []},
        {"id": "plan-2", "execution_graph": {}, "steps": []}
    ]

    ratings = await rater.rate_plans_multi_model(
        plans=plans,
        models=["claude-3.5-sonnet", "gpt-4o"],
        criteria=["feasibility", "cost_efficiency", "complexity"]
    )

    assert len(ratings) == 2  # 2 plans
    assert "plan-1" in ratings
    assert "plan-2" in ratings
    assert all("claude-3.5-sonnet" in r for r in ratings.values())
    assert all("gpt-4o" in r for r in ratings.values())


@pytest.mark.asyncio
async def test_rating_failure_fallback():
    """Test that partial ratings are returned if one model fails"""
    rater = ModelRater()

    # This will be tested with mocked LLM failures
    # For now, just ensure the service handles errors gracefully
    pass
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest backend/tests/services/test_model_rater.py::test_rate_single_plan -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.services.model_rater'"

**Step 3: Implement ModelRater service**

Create `backend/services/model_rater.py`:

```python
import asyncio
import json
from typing import List, Dict
from backend.services.llm_service import LLMService


RATING_PROMPT = """You are an expert planning analyst. Rate the following execution plan.

PLAN:
{plan_description}

EXECUTION GRAPH:
{execution_graph}

Rate each criterion from 1-10:
1. Feasibility: How likely will this plan succeed? (10 = very likely)
2. Cost Efficiency: Is this cost-effective for the value provided? (10 = excellent value)
3. Time Efficiency: Are there unnecessary delays or redundancies? (10 = very efficient)
4. Complexity: Is this appropriately scoped? (10 = too complex, 1 = too simple, 5-7 = optimal)

Provide your response as JSON:
{{
  "feasibility": <score 1-10>,
  "cost_efficiency": <score 1-10>,
  "time_efficiency": <score 1-10>,
  "complexity": <score 1-10>,
  "reasoning": "<2-3 sentence explanation>"
}}"""


class ModelRater:
    def __init__(self):
        self.llm_service = LLMService()

    async def rate_plans_multi_model(
        self,
        plans: List[Dict],
        models: List[str] = None,
        criteria: List[str] = None
    ) -> Dict[str, Dict[str, Dict]]:
        """Rate multiple plans with multiple AI models in parallel"""
        if models is None:
            models = ["claude-3.5-sonnet", "gpt-4o", "deepseek-v3"]
        if criteria is None:
            criteria = ["feasibility", "cost_efficiency", "time_efficiency", "complexity"]

        # Create all rating tasks
        tasks = []
        for plan in plans:
            for model in models:
                task = self._rate_plan_with_model(plan, model, criteria)
                tasks.append((plan["id"], model, task))

        # Execute all ratings in parallel
        results = {}
        completed_tasks = await asyncio.gather(
            *[task for _, _, task in tasks],
            return_exceptions=True
        )

        # Process results
        for (plan_id, model, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                print(f"Warning: {model} failed to rate plan {plan_id}: {result}")
                continue

            if plan_id not in results:
                results[plan_id] = {}

            results[plan_id][model] = {
                "feasibility": result["feasibility"],
                "cost_efficiency": result["cost_efficiency"],
                "time_efficiency": result["time_efficiency"],
                "complexity": result["complexity"],
                "overall_score": round(
                    (result["feasibility"] + result["cost_efficiency"] +
                     result["time_efficiency"] + (10 - abs(result["complexity"] - 5) * 2)) / 4,
                    2
                ),
                "reasoning": result["reasoning"]
            }

        return results

    async def _rate_plan_with_model(
        self,
        plan: Dict,
        model: str,
        criteria: List[str]
    ) -> Dict:
        """Rate a single plan with a specific model"""
        prompt = RATING_PROMPT.format(
            plan_description=self._describe_plan(plan),
            execution_graph=json.dumps(plan.get("execution_graph", {}), indent=2)
        )

        response = await self.llm_service.complete(
            prompt=prompt,
            model=model,
            response_format="json",
            max_tokens=500
        )

        return json.loads(response)

    def _describe_plan(self, plan: Dict) -> str:
        """Generate text description of plan"""
        steps = plan.get("steps", [])
        step_desc = "\n".join([f"- {s.get('description', 'Step')}" for s in steps])
        return f"Plan with {len(steps)} steps:\n{step_desc}"
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest backend/tests/services/test_model_rater.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/services/model_rater.py backend/tests/services/test_model_rater.py
git commit -m "feat(service): add ModelRater service for multi-model plan evaluation"
```

---

## Task 6: Backend Service - Optimizer Service (Orchestrator)

**Files:**
- Create: `backend/services/optimizer_service.py`
- Create: `backend/tests/services/test_optimizer_service.py`

**Step 1: Write test for optimizer service**

Create `backend/tests/services/test_optimizer_service.py`:

```python
import pytest
from backend.services.optimizer_service import OptimizerService


@pytest.mark.asyncio
async def test_generate_and_optimize(db_session):
    """Test full optimization workflow"""
    service = OptimizerService(db_session)

    proposal = create_mock_proposal()
    optimization = await service.optimize_proposal(
        proposal_id=proposal.id,
        optimization_types=["simplified", "enhanced"]
    )

    assert optimization["status"] == "completed"
    assert len(optimization["variants"]) == 2
    assert optimization["optimization_id"] is not None


@pytest.mark.asyncio
async def test_rate_plans_after_optimization(db_session):
    """Test rating workflow"""
    service = OptimizerService(db_session)

    # Assume variants already generated
    plan_ids = ["plan-1", "plan-2"]

    ratings = await service.rate_plans(
        session_id="session-123",
        plan_ids=plan_ids
    )

    assert ratings["status"] in ["completed", "partial"]
    assert "plan-1" in ratings["ratings"]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest backend/tests/services/test_optimizer_service.py::test_generate_and_optimize -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.services.optimizer_service'"

**Step 3: Implement OptimizerService**

Create `backend/services/optimizer_service.py`:

```python
import uuid
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from backend.services.variant_generator import VariantGenerator
from backend.services.model_rater import ModelRater
from backend.models.optimized_variant import OptimizedVariant
from backend.models.plan_rating import PlanRating
from backend.models.user_rating import UserRating
from backend.models.proposal import Proposal


class OptimizerService:
    def __init__(self, db: Session):
        self.db = db
        self.variant_generator = VariantGenerator()
        self.model_rater = ModelRater()

    async def optimize_proposal(
        self,
        proposal_id: str,
        optimization_types: List[str] = None
    ) -> Dict:
        """Generate optimized variants for a proposal"""
        # Fetch proposal
        proposal = self.db.query(Proposal).filter(Proposal.id == proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        # Generate variants
        variants = await self.variant_generator.generate_variants(
            proposal,
            types=optimization_types or ["simplified", "enhanced", "cost-optimized"]
        )

        # Save variants to database
        for variant in variants:
            self.db.add(variant)
        self.db.commit()

        return {
            "optimization_id": str(uuid.uuid4()),
            "status": "completed",
            "variants": [v.to_dict() for v in variants]
        }

    async def rate_plans(
        self,
        session_id: str,
        plan_ids: List[str],
        models: List[str] = None
    ) -> Dict:
        """Rate plans using multiple AI models"""
        # Fetch plans (proposals and variants)
        plans = []
        for plan_id in plan_ids:
            # Try to find as proposal or variant
            proposal = self.db.query(Proposal).filter(Proposal.id == plan_id).first()
            if proposal:
                plans.append({
                    "id": str(proposal.id),
                    "execution_graph": proposal.execution_graph,
                    "steps": proposal.steps
                })
                continue

            variant = self.db.query(OptimizedVariant).filter(
                OptimizedVariant.id == plan_id
            ).first()
            if variant:
                plans.append({
                    "id": str(variant.id),
                    "execution_graph": variant.execution_graph,
                    "steps": variant.steps
                })

        if not plans:
            raise ValueError(f"No plans found for IDs: {plan_ids}")

        # Rate with multiple models
        ratings = await self.model_rater.rate_plans_multi_model(
            plans=plans,
            models=models or ["claude-3.5-sonnet", "gpt-4o", "deepseek-v3"]
        )

        # Save ratings to database
        for plan_id, model_ratings in ratings.items():
            for model_name, rating_data in model_ratings.items():
                rating = PlanRating(
                    session_id=session_id,
                    plan_id=plan_id,
                    model_name=model_name,
                    ratings={
                        "feasibility": rating_data["feasibility"],
                        "cost_efficiency": rating_data["cost_efficiency"],
                        "time_efficiency": rating_data["time_efficiency"],
                        "complexity": rating_data["complexity"],
                        "overall_score": rating_data["overall_score"]
                    },
                    reasoning=rating_data["reasoning"]
                )
                self.db.add(rating)

        self.db.commit()

        return {
            "rating_id": str(uuid.uuid4()),
            "status": "completed",
            "ratings": ratings
        }

    def save_user_rating(
        self,
        session_id: str,
        plan_id: str,
        rating: int,
        comment: Optional[str] = None,
        rationale: Optional[str] = None
    ) -> Dict:
        """Save user's rating for a plan"""
        user_rating = UserRating(
            session_id=session_id,
            plan_id=plan_id,
            rating=rating,
            comment=comment,
            rationale=rationale
        )
        self.db.add(user_rating)
        self.db.commit()

        return {
            "saved": True,
            "rating_id": str(user_rating.id)
        }

    def get_optimization_state(
        self,
        session_id: str
    ) -> Dict:
        """Get current state of optimization for a session"""
        variants = self.db.query(OptimizedVariant).filter(
            OptimizedVariant.session_id == session_id
        ).all()

        ratings = self.db.query(PlanRating).filter(
            PlanRating.session_id == session_id
        ).all()

        return {
            "status": "completed" if variants and ratings else "in_progress",
            "phase": "rating" if variants else "generating_variants",
            "progress": {
                "variants_generated": len(variants),
                "variants_total": 3,
                "ratings_completed": len(ratings),
                "ratings_total": 9  # 3 plans × 3 models
            }
        }
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest backend/tests/services/test_optimizer_service.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/services/optimizer_service.py backend/tests/services/test_optimizer_service.py
git commit -m "feat(service): add OptimizerService to coordinate variants and ratings"
```

---

## Task 7: Backend API Routes

**Files:**
- Create: `backend/routes/optimizer_routes.py`
- Modify: `backend/main.py` (register routes)

**Step 1: Write test for API endpoints**

Create `backend/tests/api/test_optimizer_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient


def test_optimize_proposal(client, db_session, auth_token):
    """Test POST /sessions/{id}/optimize"""
    response = client.post(
        "/api/v1/sessions/session-123/optimize",
        json={
            "selected_proposal_id": "proposal-123",
            "optimization_types": ["simplified"]
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "variants" in data


def test_rate_plans(client, db_session, auth_token):
    """Test POST /sessions/{id}/rate"""
    response = client.post(
        "/api/v1/sessions/session-123/rate",
        json={
            "plan_ids": ["plan-1", "plan-2"],
            "models": ["claude-3.5-sonnet"]
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "ratings" in data


def test_save_user_rating(client, db_session, auth_token):
    """Test POST /sessions/{id}/user-rating"""
    response = client.post(
        "/api/v1/sessions/session-123/user-rating",
        json={
            "plan_id": "plan-123",
            "rating": 5,
            "comment": "Great plan"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    assert response.json()["saved"] is True


def test_get_optimization_state(client, db_session, auth_token):
    """Test GET /sessions/{id}/optimization-state"""
    response = client.get(
        "/api/v1/sessions/session-123/optimization-state",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "progress" in data
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest backend/tests/api/test_optimizer_routes.py -v`
Expected: FAIL with 404 Not Found (routes don't exist yet)

**Step 3: Implement API routes**

Create `backend/routes/optimizer_routes.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.optimizer import (
    OptimizerRequest,
    OptimizerResponse,
    RatePlansRequest,
    RatePlansResponse,
    UserRatingRequest,
    UserRatingResponse,
    OptimizationStateResponse
)
from backend.services.optimizer_service import OptimizerService
from backend.auth import get_current_user  # Existing auth

router = APIRouter(prefix="/api/v1/sessions/{session_id}", tags=["optimizer"])


@router.post("/optimize", response_model=OptimizerResponse)
async def optimize_proposal(
    session_id: str,
    request: OptimizerRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate optimized variants of a selected proposal"""
    try:
        service = OptimizerService(db)
        result = await service.optimize_proposal(
            proposal_id=request.selected_proposal_id,
            optimization_types=request.optimization_types
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.post("/rate", response_model=RatePlansResponse)
async def rate_plans(
    session_id: str,
    request: RatePlansRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Rate plans using multiple AI models"""
    try:
        service = OptimizerService(db)
        result = await service.rate_plans(
            session_id=session_id,
            plan_ids=request.plan_ids,
            models=request.models
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rating failed: {str(e)}")


@router.post("/user-rating", response_model=UserRatingResponse)
async def save_user_rating(
    session_id: str,
    request: UserRatingRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Save user's rating and comments for a plan"""
    try:
        service = OptimizerService(db)
        result = service.save_user_rating(
            session_id=session_id,
            plan_id=request.plan_id,
            rating=request.rating,
            comment=request.comment,
            rationale=request.rationale
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save rating: {str(e)}")


@router.get("/optimization-state", response_model=OptimizationStateResponse)
async def get_optimization_state(
    session_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get current optimization progress and state"""
    try:
        service = OptimizerService(db)
        result = service.get_optimization_state(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get state: {str(e)}")
```

**Step 4: Register routes in main app**

Open `backend/main.py`, add:

```python
from backend.routes.optimizer_routes import router as optimizer_router

# Add after existing router includes
app.include_router(optimizer_router)
```

**Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest backend/tests/api/test_optimizer_routes.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add backend/routes/optimizer_routes.py backend/main.py backend/tests/api/test_optimizer_routes.py
git commit -m "feat(api): add optimizer API endpoints"
```

---

## Task 8: Backend SSE Events for Real-time Updates

**Files:**
- Modify: `backend/routes/optimizer_routes.py` (add SSE endpoints)
- Create: `backend/services/sse_manager.py`

**Step 1: Create SSE manager**

Create `backend/services/sse_manager.py`:

```python
from typing import Dict, AsyncIterator
from fastapi import Request
import json
import asyncio


class SSEManager:
    """Manages Server-Sent Events connections for real-time updates"""

    def __init__(self):
        self._connections: Dict[str, list] = {}

    async def subscribe(self, session_id: str) -> AsyncIterator[dict]:
        """Subscribe to SSE events for a session"""
        queue = asyncio.Queue()

        if session_id not in self._connections:
            self._connections[session_id] = []
        self._connections[session_id].append(queue)

        try:
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            self._connections[session_id].remove(queue)
            if not self._connections[session_id]:
                del self._connections[session_id]
            raise

    async def broadcast(self, session_id: str, event_type: str, data: dict):
        """Broadcast event to all subscribers of a session"""
        if session_id not in self._connections:
            return

        event = {
            "type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }

        for queue in self._connections[session_id]:
            await queue.put(event)


# Global SSE manager instance
sse_manager = SSEManager()
```

**Step 2: Add SSE endpoint to routes**

Open `backend/routes/optimizer_routes.py`, add:

```python
from fastapi import Request
from backend.services.sse_manager import sse_manager


@router.get("/optimization-stream")
async def optimization_stream(
    session_id: str,
    request: Request
):
    """SSE endpoint for real-time optimization updates"""

    async def event_stream():
        try:
            async for event in sse_manager.subscribe(session_id):
                yield f"event: {event['type']}\n"
                yield f"data: {json.dumps(event['data'])}\n\n"
        except asyncio.CancelledError:
            return

    return EventSourceResponse(event_stream())
```

**Step 3: Update services to broadcast SSE events**

Modify `backend/services/optimizer_service.py`:

```python
from backend.services.sse_manager import sse_manager


class OptimizerService:
    # ... existing code ...

    async def optimize_proposal(self, proposal_id: str, optimization_types: List[str] = None):
        # Broadcast start
        await sse_manager.broadcast(
            proposal_id,
            "optimization_started",
            {"message": "Generating optimized variants..."}
        )

        variants = await self.variant_generator.generate_variants(...)

        # Broadcast each variant
        for variant in variants:
            await sse_manager.broadcast(
                proposal_id,
                "variant_generated",
                {"variant_id": str(variant.id), "type": variant.variant_type}
            )

        # Broadcast completion
        await sse_manager.broadcast(
            proposal_id,
            "variants_complete",
            {"count": len(variants)}
        )

        return {...}

    async def rate_plans(self, session_id: str, plan_ids: List[str], models: List[str] = None):
        await sse_manager.broadcast(
            session_id,
            "rating_started",
            {"plans_count": len(plan_ids)}
        )

        # ... rating logic ...

        for plan_id, model_ratings in ratings.items():
            await sse_manager.broadcast(
                session_id,
                "model_rated",
                {"plan_id": plan_id, "models_completed": len(model_ratings)}
            )

        await sse_manager.broadcast(
            session_id,
            "ratings_complete",
            {"total_ratings": sum(len(r) for r in ratings.values())}
        )

        return {...}
```

**Step 4: Commit**

```bash
git add backend/services/sse_manager.py backend/routes/optimizer_routes.py backend/services/optimizer_service.py
git commit -m "feat(sse): add real-time optimization updates via SSE"
```

---

## Task 9: Frontend - TypeScript Types

**Files:**
- Create: `frontend/src/types/optimizer.ts`

**Step 1: Create type definitions**

Create `frontend/src/types/optimizer.ts`:

```typescript
export type VariantType = 'simplified' | 'enhanced' | 'cost-optimized';

export interface OptimizedVariant {
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

export interface ModelRating {
  modelName: string;
  feasibility: number;
  costEfficiency: number;
  timeEfficiency: number;
  complexity: number;
  overallScore: number;
  reasoning: string;
}

export interface PlanRatings {
  planId: string;
  ratings: {
    [modelName: string]: ModelRating;
  };
  averageScore: number;
  consensus: number;
}

export interface UserRating {
  planId: string;
  rating: number;
  comment?: string;
  rationale?: string;
  timestamp: Date;
}

export interface OptimizerState {
  status: 'idle' | 'generating_variants' | 'rating' | 'completed' | 'error';
  selectedProposalId: string;
  variants: OptimizedVariant[];
  ratings: PlanRatings[];
  userRating?: UserRating;
  executionChoice?: string;
  progress: {
    variantsGenerated: number;
    variantsTotal: number;
    ratingsCompleted: number;
    ratingsTotal: number;
  };
  error?: string;
}

export interface PlanComparison {
  planId: string;
  planName: string;
  planType: 'original' | VariantType;
  metrics: {
    cost: number;
    time: number;
    feasibility: number;
    stepCount: number;
  };
  aiScores: {
    [modelName: string]: number;
  };
  averageAiScore: number;
  userRating?: number;
}

// Re-use existing types
export interface ExecutionGraph {
  nodes: Array<{ id: string; [key: string]: any }>;
  edges: Array<{ source: string; target: string; [key: string]: any }>;
}

export interface ExecutionStep {
  id: string;
  description: string;
  model: string;
  dependencies: string[];
  [key: string]: any;
}
```

**Step 2: Export from types index**

Open `frontend/src/types/index.ts`, add:

```typescript
export * from './optimizer';
```

**Step 3: Commit**

```bash
git add frontend/src/types/optimizer.ts frontend/src/types/index.ts
git commit -m "feat(types): add optimizer TypeScript type definitions"
```

---

## Task 10: Frontend - Custom Hooks

**Files:**
- Create: `frontend/src/hooks/useOptimizer.ts`
- Create: `frontend/src/hooks/useOptimizerSSE.ts`
- Modify: `frontend/src/hooks/index.ts`

**Step 1: Write tests for useOptimizer hook**

Create `frontend/src/hooks/__tests__/useOptimizer.test.ts`:

```typescript
import { renderHook, act, waitFor } from '@testing-library/react';
import { useOptimizer } from '../useOptimizer';

// Mock API
jest.mock('../useApi', () => ({
  useApi: () => ({
    post: jest.fn()
  })
}));

describe('useOptimizer', () => {
  it('initializes with idle state', () => {
    const { result } = renderHook(() => useOptimizer('session-123'));

    expect(result.current.state.status).toBe('idle');
    expect(result.current.state.variants).toEqual([]);
  });

  it('generates variants and updates state', async () => {
    const mockPost = jest.fn().mockResolvedValue({
      data: {
        variants: [
          { id: 'v1', type: 'simplified', name: 'Simplified', ... }
        ]
      }
    });

    const { result } = renderHook(() => useOptimizer('session-123'));

    await act(async () => {
      await result.current.generateVariants('proposal-123');
    });

    await waitFor(() => {
      expect(result.current.state.variants).toHaveLength(1);
      expect(result.current.state.variants[0].type).toBe('simplified');
    });
  });

  it('handles API errors', async () => {
    const mockPost = jest.fn().mockRejectedValue(new Error('API Error'));

    const { result } = renderHook(() => useOptimizer('session-123'));

    await act(async () => {
      await result.current.generateVariants('proposal-123');
    });

    expect(result.current.state.status).toBe('error');
    expect(result.current.error).toBeDefined();
  });
});
```

**Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test useOptimizer.test.ts`
Expected: FAIL with "Cannot find module 'useOptimizer'"

**Step 3: Implement useOptimizer hook**

Create `frontend/src/hooks/useOptimizer.ts`:

```typescript
import { useState, useCallback } from 'react';
import { useApi } from './useApi';
import { OptimizerState, OptimizedVariant, PlanRatings, UserRating } from '../types/optimizer';

export const useOptimizer = (sessionId: string) => {
  const api = useApi();
  const [state, setState] = useState<OptimizerState>({
    status: 'idle',
    selectedProposalId: '',
    variants: [],
    ratings: [],
    progress: {
      variantsGenerated: 0,
      variantsTotal: 0,
      ratingsCompleted: 0,
      ratingsTotal: 0,
    },
  });
  const [error, setError] = useState<string>();

  const generateVariants = useCallback(async (proposalId: string) => {
    setState(prev => ({
      ...prev,
      status: 'generating_variants',
      selectedProposalId: proposalId,
    }));

    try {
      const response = await api.post(`/sessions/${sessionId}/optimize`, {
        selected_proposal_id: proposalId,
        optimization_types: ['simplified', 'enhanced', 'cost-optimized'],
      });

      setState(prev => ({
        ...prev,
        variants: response.data.variants,
        progress: {
          ...prev.progress,
          variantsGenerated: response.data.variants.length,
          variantsTotal: response.data.variants.length,
        },
      }));

      return response.data;
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to generate variants';
      setError(errorMsg);
      setState(prev => ({ ...prev, status: 'error' }));
      throw err;
    }
  }, [sessionId, api]);

  const ratePlans = useCallback(async () => {
    setState(prev => ({ ...prev, status: 'rating' }));

    const planIds = [
      state.selectedProposalId,
      ...state.variants.map(v => v.id),
    ];

    try {
      const response = await api.post(`/sessions/${sessionId}/rate`, {
        plan_ids: planIds,
        models: ['claude-3.5-sonnet', 'gpt-4o', 'deepseek-v3'],
        criteria: ['feasibility', 'cost_efficiency', 'time_efficiency', 'complexity'],
      });

      setState(prev => ({
        ...prev,
        ratings: response.data.ratings,
        progress: {
          ...prev.progress,
          ratingsCompleted: Object.keys(response.data.ratings).length * 3,
          ratingsTotal: Object.keys(response.data.ratings).length * 3,
        },
        status: 'completed',
      }));

      return response.data;
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to rate plans';
      setError(errorMsg);
      setState(prev => ({ ...prev, status: 'error' }));
      throw err;
    }
  }, [sessionId, state.selectedProposalId, state.variants, api]);

  const saveUserRating = useCallback(async (rating: UserRating) => {
    try {
      await api.post(`/sessions/${sessionId}/user-rating`, rating);
      setState(prev => ({ ...prev, userRating: rating }));
    } catch (err: any) {
      setError('Failed to save rating');
      throw err;
    }
  }, [sessionId, api]);

  const setExecutionChoice = useCallback((planId: string) => {
    setState(prev => ({ ...prev, executionChoice: planId }));
  }, []);

  return {
    state,
    error,
    generateVariants,
    ratePlans,
    saveUserRating,
    setExecutionChoice,
  };
};
```

**Step 4: Implement useOptimizerSSE hook**

Create `frontend/src/hooks/useOptimizerSSE.ts`:

```typescript
import { useState, useEffect } from 'react';
import { OptimizerEvent } from '../types/optimizer';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export const useOptimizerSSE = (sessionId: string) => {
  const [events, setEvents] = useState<OptimizerEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const eventSource = new EventSource(
      `${API_BASE}/api/v1/sessions/${sessionId}/optimization-stream`
    );

    eventSource.onopen = () => setIsConnected(true);
    eventSource.onerror = () => setIsConnected(false);

    eventSource.addEventListener('variant_generated', (e) => {
      const data = JSON.parse(e.data);
      setEvents(prev => [...prev, { type: 'variant', data }]);
    });

    eventSource.addEventListener('model_rated', (e) => {
      const data = JSON.parse(e.data);
      setEvents(prev => [...prev, { type: 'rating', data }]);
    });

    eventSource.addEventListener('ratings_complete', () => {
      setEvents(prev => [...prev, { type: 'complete', data: null }]);
    });

    return () => eventSource.close();
  }, [sessionId]);

  return { events, isConnected };
};
```

**Step 5: Update hooks index**

Open `frontend/src/hooks/index.ts`, add:

```typescript
export { useOptimizer } from './useOptimizer';
export { useOptimizerSSE } from './useOptimizerSSE';
```

**Step 6: Run tests**

Run: `cd frontend && npm test useOptimizer.test.ts`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add frontend/src/hooks/useOptimizer.ts frontend/src/hooks/useOptimizerSSE.ts frontend/src/hooks/__tests__/useOptimizer.test.ts frontend/src/hooks/index.ts
git commit -m "feat(hooks): add useOptimizer and useOptimizerSSE hooks"
```

---

## Task 11: Frontend - PlanCard Component (Enhanced)

**Files:**
- Modify: `frontend/src/components/PlanCard.tsx` (or create if doesn't exist)

**Step 1: Create PlanCard component**

Create `frontend/src/components/PlanCard.tsx`:

```typescript
import React, { memo } from 'react';
import { Check, Star, Clock, DollarSign } from 'lucide-react';
import { OptimizedVariant } from '../types/optimizer';

interface PlanCardProps {
  plan: {
    id: string;
    name: string;
    description: string;
    executionGraph: any;
    steps: any[];
    metadata?: {
      stepCount: number;
      estimatedCost: number;
      estimatedTime: number;
    };
    variantType?: 'original' | 'simplified' | 'enhanced' | 'cost-optimized';
  };
  isSelected: boolean;
  onSelect: () => void;
}

export const PlanCard = memo(({ plan, isSelected, onSelect }: PlanCardProps) => {
  const variantColors = {
    original: 'border-blue-500',
    simplified: 'border-green-500',
    enhanced: 'border-purple-500',
    'cost-optimized': 'border-amber-500',
  };

  const variantBadges = {
    original: 'bg-blue-500/20 text-blue-400',
    simplified: 'bg-green-500/20 text-green-400',
    enhanced: 'bg-purple-500/20 text-purple-400',
    'cost-optimized': 'bg-amber-500/20 text-amber-400',
  };

  return (
    <div
      onClick={onSelect}
      className={`
        relative p-4 rounded-lg border-2 cursor-pointer transition-all
        ${isSelected ? 'border-primary bg-primary/10' : variantColors[plan.variantType || 'original'] + ' border-opacity-30'}
        hover:border-opacity-100
      `}
    >
      {isSelected && (
        <div className="absolute top-2 right-2">
          <Check className="w-5 h-5 text-primary" />
        </div>
      )}

      <div className="mb-2">
        <span className={`text-xs px-2 py-1 rounded ${variantBadges[plan.variantType || 'original']}`}>
          {plan.variantType || 'original'}
        </span>
      </div>

      <h3 className="text-lg font-semibold mb-1">{plan.name}</h3>
      <p className="text-sm text-gray-400 mb-3">{plan.description}</p>

      {plan.metadata && (
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-1">
            <DollarSign className="w-4 h-4 text-green-400" />
            <span>${plan.metadata.estimatedCost.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="w-4 h-4 text-blue-400" />
            <span>{plan.metadata.estimatedTime}m</span>
          </div>
          <div className="flex items-center gap-1">
            <Star className="w-4 h-4 text-amber-400" />
            <span>{plan.metadata.stepCount} steps</span>
          </div>
        </div>
      )}
    </div>
  );
});
```

**Step 2: Commit**

```bash
git add frontend/src/components/PlanCard.tsx
git commit -m "feat(component): add PlanCard component with variant styling"
```

---

## Task 12: Frontend - ComparisonPanel Component

**Files:**
- Create: `frontend/src/components/optimizer/ComparisonPanel.tsx`
- Create: `frontend/src/components/optimizer/ComparisonTable.tsx`
- Create: `frontend/src/components/optimizer/RadarChart.tsx`

**Step 1: Create ComparisonPanel**

Create `frontend/src/components/optimizer/ComparisonPanel.tsx`:

```typescript
import React, { useState } from 'react';
import { ComparisonTable } from './ComparisonTable';
import { RadarChart } from './RadarChart';
import { ModelRatingsDisplay } from './ModelRatingsDisplay';
import { UserRatingControl } from './UserRatingControl';
import { PlanComparison } from '../../types/optimizer';

interface ComparisonPanelProps {
  comparisons: PlanComparison[];
  userRating?: { planId: string; rating: number };
  onUserRate: (planId: string, rating: number, comment?: string) => void;
}

export const ComparisonPanel: React.FC<ComparisonPanelProps> = ({
  comparisons,
  userRating,
  onUserRate,
}) => {
  const [activeTab, setActiveTab] = useState<'table' | 'radar' | 'ratings'>('table');

  return (
    <div className="bg-surface rounded-lg p-4">
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('table')}
          className={`px-4 py-2 rounded ${activeTab === 'table' ? 'bg-primary text-white' : 'bg-gray-700'}`}
        >
          Comparison Table
        </button>
        <button
          onClick={() => setActiveTab('radar')}
          className={`px-4 py-2 rounded ${activeTab === 'radar' ? 'bg-primary text-white' : 'bg-gray-700'}`}
        >
          Radar Chart
        </button>
        <button
          onClick={() => setActiveTab('ratings')}
          className={`px-4 py-2 rounded ${activeTab === 'ratings' ? 'bg-primary text-white' : 'bg-gray-700'}`}
        >
          AI Ratings
        </button>
      </div>

      {activeTab === 'table' && <ComparisonTable comparisons={comparisons} />}
      {activeTab === 'radar' && <RadarChart comparisons={comparisons} />}
      {activeTab === 'ratings' && (
        <>
          <ModelRatingsDisplay comparisons={comparisons} />
          <UserRatingControl
            comparisons={comparisons}
            currentRating={userRating}
            onRate={onUserRate}
          />
        </>
      )}
    </div>
  );
};
```

**Step 2: Create ComparisonTable component**

Create `frontend/src/components/optimizer/ComparisonTable.tsx`:

```typescript
import React from 'react';
import { PlanComparison } from '../../types/optimizer';

interface ComparisonTableProps {
  comparisons: PlanComparison[];
}

export const ComparisonTable: React.FC<ComparisonTableProps> = ({ comparisons }) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="text-left p-2">Plan</th>
            <th className="text-right p-2">Cost</th>
            <th className="text-right p-2">Time</th>
            <th className="text-right p-2">Feasibility</th>
            <th className="text-right p-2">Steps</th>
            <th className="text-right p-2">AI Score</th>
          </tr>
        </thead>
        <tbody>
          {comparisons.map((comparison) => (
            <tr key={comparison.planId} className="border-b border-gray-800">
              <td className="p-2 font-medium">{comparison.planName}</td>
              <td className="text-right p-2 text-green-400">${comparison.metrics.cost.toFixed(2)}</td>
              <td className="text-right p-2 text-blue-400">{comparison.metrics.time}m</td>
              <td className="text-right p-2">{comparison.metrics.feasibility.toFixed(1)}/10</td>
              <td className="text-right p-2">{comparison.metrics.stepCount}</td>
              <td className="text-right p-2 font-bold text-primary">
                {comparison.averageAiScore.toFixed(1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

**Step 3: Create simple RadarChart component**

Create `frontend/src/components/optimizer/RadarChart.tsx`:

```typescript
import React from 'react';
import { PlanComparison } from '../../types/optimizer';

interface RadarChartProps {
  comparisons: PlanComparison[];
}

export const RadarChart: React.FC<RadarChartProps> = ({ comparisons }) => {
  // Simple SVG-based radar chart
  const maxScore = 10;
  const size = 300;
  const center = size / 2;
  const radius = size / 2 - 40;

  const criteria = ['Cost Efficiency', 'Speed', 'Feasibility'];

  const getPoint = (value: number, index: number, total: number) => {
    const angle = (index * 2 * Math.PI) / total - Math.PI / 2;
    const distance = (value / maxScore) * radius;
    return {
      x: center + distance * Math.cos(angle),
      y: center + distance * Math.sin(angle),
    };
  };

  const colors = ['#38bdf8', '#22c55e', '#a855f7'];

  return (
    <div className="flex justify-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background grid */}
        {[0.2, 0.4, 0.6, 0.8, 1].map((scale) => (
          <polygon
            key={scale}
            points={criteria
              .map((_, i) => {
                const point = getPoint(maxScore * scale, i, criteria.length);
                return `${point.x},${point.y}`;
              })
              .join(' ')}
            fill="none"
            stroke="#374151"
            strokeWidth="1"
          />
        ))}

        {/* Axes */}
        {criteria.map((_, i) => {
          const point = getPoint(maxScore, i, criteria.length);
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={point.x}
              y2={point.y}
              stroke="#374151"
              strokeWidth="1"
            />
          );
        })}

        {/* Data polygons */}
        {comparisons.map((comparison, idx) => {
          const scores = [
            (10 - comparison.metrics.cost / 5), // Normalize cost
            (10 - comparison.metrics.time / 3), // Normalize time
            comparison.metrics.feasibility,
          ];

          const points = scores.map((score, i) => {
            const point = getPoint(score, i, criteria.length);
            return `${point.x},${point.y}`;
          });

          return (
            <polygon
              key={comparison.planId}
              points={points.join(' ')}
              fill={colors[idx % colors.length]}
              fillOpacity="0.2"
              stroke={colors[idx % colors.length]}
              strokeWidth="2"
            />
          );
        })}

        {/* Labels */}
        {criteria.map((criterion, i) => {
          const point = getPoint(maxScore * 1.1, i, criteria.length);
          return (
            <text
              key={i}
              x={point.x}
              y={point.y}
              textAnchor="middle"
              fill="#9CA3AF"
              fontSize="12"
            >
              {criterion}
            </text>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="ml-4">
        {comparisons.map((comparison, idx) => (
          <div key={comparison.planId} className="flex items-center gap-2 mb-2">
            <div
              className="w-4 h-4 rounded"
              style={{ backgroundColor: colors[idx % colors.length] }}
            />
            <span className="text-sm">{comparison.planName}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

**Step 4: Create ModelRatingsDisplay component**

Create `frontend/src/components/optimizer/ModelRatingsDisplay.tsx`:

```typescript
import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { PlanComparison } from '../../types/optimizer';

interface ModelRatingsDisplayProps {
  comparisons: PlanComparison[];
}

export const ModelRatingsDisplay: React.FC<ModelRatingsDisplayProps> = ({ comparisons }) => {
  const [expandedPlan, setExpandedPlan] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      {comparisons.map((comparison) => (
        <div key={comparison.planId} className="border border-gray-700 rounded-lg">
          <button
            onClick={() => setExpandedPlan(expandedPlan === comparison.planId ? null : comparison.planId)}
            className="w-full p-3 flex justify-between items-center hover:bg-gray-800"
          >
            <span className="font-medium">{comparison.planName}</span>
            {expandedPlan === comparison.planId ? (
              <ChevronDown className="w-5 h-5" />
            ) : (
              <ChevronRight className="w-5 h-5" />
            )}
          </button>

          {expandedPlan === comparison.planId && (
            <div className="p-3 border-t border-gray-700 space-y-2">
              {Object.entries(comparison.aiScores).map(([model, score]) => (
                <div key={model} className="flex justify-between items-center">
                  <span className="text-sm text-gray-400">{model}</span>
                  <span className={`font-bold ${
                    score >= 8 ? 'text-green-400' :
                    score >= 6 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>
                    {score.toFixed(1)}/10
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
```

**Step 5: Create UserRatingControl component**

Create `frontend/src/components/optimizer/UserRatingControl.tsx`:

```typescript
import React, { useState } from 'react';
import { Star } from 'lucide-react';
import { PlanComparison } from '../../types/optimizer';

interface UserRatingControlProps {
  comparisons: PlanComparison[];
  currentRating?: { planId: string; rating: number };
  onRate: (planId: string, rating: number, comment?: string) => void;
}

export const UserRatingControl: React.FC<UserRatingControlProps> = ({
  comparisons,
  currentRating,
  onRate,
}) => {
  const [selectedPlan, setSelectedPlan] = useState<string>(comparisons[0]?.planId || '');
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');

  const handleSubmit = () => {
    if (rating > 0 && selectedPlan) {
      onRate(selectedPlan, rating, comment);
    }
  };

  return (
    <div className="mt-6 border-t border-gray-700 pt-4">
      <h3 className="text-lg font-semibold mb-3">Your Rating</h3>

      <select
        value={selectedPlan}
        onChange={(e) => setSelectedPlan(e.target.value)}
        className="w-full p-2 bg-background border border-gray-700 rounded mb-3"
      >
        {comparisons.map((c) => (
          <option key={c.planId} value={c.planId}>{c.planName}</option>
        ))}
      </select>

      <div className="flex gap-2 mb-3">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onClick={() => setRating(star)}
            className="hover:scale-110 transition"
          >
            <Star
              className={`w-8 h-8 ${
                star <= rating ? 'fill-amber-400 text-amber-400' : 'text-gray-600'
              }`}
            />
          </button>
        ))}
      </div>

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Why did you choose this plan?"
        className="w-full p-2 bg-background border border-gray-700 rounded mb-3"
        rows={2}
      />

      <button
        onClick={handleSubmit}
        disabled={rating === 0}
        className="w-full py-2 bg-primary hover:bg-primary/80 disabled:bg-gray-700 rounded font-medium"
      >
        Save Rating
      </button>
    </div>
  );
};
```

**Step 6: Commit**

```bash
git add frontend/src/components/optimizer/
git commit -m "feat(components): add comparison panel with table, chart, and rating controls"
```

---

## Task 13: Frontend - OptimizerStage Main Component

**Files:**
- Create: `frontend/src/components/optimizer/OptimizerStage.tsx`
- Create: `frontend/src/components/optimizer/OptimizerHeader.tsx`
- Create: `frontend/src/components/optimizer/PlanCardsPanel.tsx`
- Create: `frontend/src/components/optimizer/OptimizerFooter.tsx`

**Step 1: Create OptimizerStage**

Create `frontend/src/components/optimizer/OptimizerStage.tsx`:

```typescript
import React, { useEffect, useState } from 'react';
import { useOptimizer, useOptimizerSSE } from '../../hooks';
import { OptimizerHeader } from './OptimizerHeader';
import { PlanCardsPanel } from './PlanCardsPanel';
import { ComparisonPanel } from './ComparisonPanel';
import { OptimizerFooter } from './OptimizerFooter';
import { PlanComparison } from '../../types/optimizer';

interface OptimizerStageProps {
  sessionId: string;
  selectedProposalId: string;
  onComplete: (chosenPlanId: string) => void;
  onBack: () => void;
}

export const OptimizerStage: React.FC<OptimizerStageProps> = ({
  sessionId,
  selectedProposalId,
  onComplete,
  onBack,
}) => {
  const { state, generateVariants, ratePlans, saveUserRating, setExecutionChoice } = useOptimizer(sessionId);
  const { events, isConnected } = useOptimizerSSE(sessionId);
  const [selectedPlan, setSelectedPlan] = useState<string>(selectedProposalId);

  useEffect(() => {
    // Auto-start optimization
    generateVariants(selectedProposalId);
  }, [selectedProposalId, generateVariants]);

  useEffect(() => {
    // Auto-trigger rating when variants are ready
    if (state.status === 'generating_variants' && state.variants.length > 0) {
      ratePlans();
    }
  }, [state.variants, state.status, ratePlans]);

  const handleSelectPlan = (planId: string) => {
    setSelectedPlan(planId);
    setExecutionChoice(planId);
  };

  const handleUserRate = async (planId: string, rating: number, comment?: string) => {
    await saveUserRating({
      planId,
      rating,
      comment,
      timestamp: new Date(),
    });
  };

  const handleExecute = () => {
    if (selectedPlan) {
      onComplete(selectedPlan);
    }
  };

  // Build comparison data
  const comparisons: PlanComparison[] = [
    {
      planId: selectedProposalId,
      planName: 'Original Proposal',
      planType: 'original',
      metrics: {
        cost: 2.50,
        time: 15,
        feasibility: 8.5,
        stepCount: 10,
      },
      aiScores: {},
      averageAiScore: 0,
    },
    ...state.variants.map((v) => ({
      planId: v.id,
      planName: v.name,
      planType: v.type,
      metrics: {
        cost: v.metadata.estimatedCost,
        time: v.metadata.estimatedTime,
        feasibility: 8.0,
        stepCount: v.metadata.stepCount,
      },
      aiScores: {},
      averageAiScore: 0,
    })),
  ];

  if (state.status === 'error') {
    return (
      <div className="p-8 text-center">
        <p className="text-red-500 mb-4">{state.error || 'Optimization failed'}</p>
        <button onClick={onBack} className="px-4 py-2 bg-primary rounded">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <OptimizerHeader onBack={onBack} />

      <div className="flex-1 overflow-auto p-4">
        {state.status === 'generating_variants' && (
          <div className="text-center py-12">
            <div className="text-2xl mb-4">🤖 AI is optimizing your plan...</div>
            <div className="w-64 mx-auto bg-gray-800 rounded-full h-4">
              <div
                className="bg-primary h-4 rounded-full transition-all"
                style={{ width: `${(state.progress.variantsGenerated / 3) * 100}%` }}
              />
            </div>
            <p className="text-gray-400 mt-2">
              Generating variants: {state.progress.variantsGenerated}/3
            </p>
          </div>
        )}

        {state.status === 'rating' && (
          <div className="text-center py-12">
            <div className="text-2xl mb-4">📊 Gathering AI model ratings...</div>
            <p className="text-gray-400">
              Ratings complete: {state.progress.ratingsCompleted}/9
            </p>
          </div>
        )}

        {state.status === 'completed' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <PlanCardsPanel
              selectedProposalId={selectedProposalId}
              variants={state.variants}
              selectedPlan={selectedPlan}
              onSelectPlan={handleSelectPlan}
            />
            <ComparisonPanel
              comparisons={comparisons}
              userRating={state.userRating}
              onUserRate={handleUserRate}
            />
          </div>
        )}
      </div>

      <OptimizerFooter
        selectedPlan={selectedPlan}
        canExecute={state.status === 'completed'}
        onExecute={handleExecute}
      />
    </div>
  );
};
```

**Step 2: Create supporting components**

Create `frontend/src/components/optimizer/OptimizerHeader.tsx`:

```typescript
import React from 'react';
import { ArrowLeft } from 'lucide-react';

interface OptimizerHeaderProps {
  onBack: () => void;
}

export const OptimizerHeader: React.FC<OptimizerHeaderProps> = ({ onBack }) => {
  return (
    <div className="p-4 border-b border-gray-800 flex justify-between items-center">
      <h1 className="text-2xl font-bold">Plan Optimizer</h1>
      <button onClick={onBack} className="flex items-center gap-2 text-gray-400 hover:text-white">
        <ArrowLeft className="w-5 h-5" />
        Back to Proposals
      </button>
    </div>
  );
};
```

Create `frontend/src/components/optimizer/PlanCardsPanel.tsx`:

```typescript
import React from 'react';
import { PlanCard } from '../PlanCard';
import { OptimizedVariant } from '../../types/optimizer';

interface PlanCardsPanelProps {
  selectedProposalId: string;
  variants: OptimizedVariant[];
  selectedPlan: string;
  onSelectPlan: (planId: string) => void;
}

export const PlanCardsPanel: React.FC<PlanCardsPanelProps> = ({
  selectedProposalId,
  variants,
  selectedPlan,
  onSelectPlan,
}) => {
  // Mock original proposal data
  const originalProposal = {
    id: selectedProposalId,
    name: 'Original Proposal',
    description: 'The proposal you selected',
    executionGraph: { nodes: [], edges: [] },
    steps: [],
    metadata: { stepCount: 10, estimatedCost: 2.5, estimatedTime: 15 },
    variantType: 'original' as const,
  };

  return (
    <div className="space-y-3">
      <h2 className="text-xl font-semibold mb-3">Select a Plan</h2>
      <PlanCard
        plan={originalProposal}
        isSelected={selectedPlan === selectedProposalId}
        onSelect={() => onSelectPlan(selectedProposalId)}
      />
      {variants.map((variant) => (
        <PlanCard
          key={variant.id}
          plan={{
            id: variant.id,
            name: variant.name,
            description: variant.description,
            executionGraph: variant.executionGraph,
            steps: variant.steps,
            metadata: variant.metadata,
            variantType: variant.type,
          }}
          isSelected={selectedPlan === variant.id}
          onSelect={() => onSelectPlan(variant.id)}
        />
      ))}
    </div>
  );
};
```

Create `frontend/src/components/optimizer/OptimizerFooter.tsx`:

```typescript
import React from 'react';

interface OptimizerFooterProps {
  selectedPlan: string;
  canExecute: boolean;
  onExecute: () => void;
}

export const OptimizerFooter: React.FC<OptimizerFooterProps> = ({
  selectedPlan,
  canExecute,
  onExecute,
}) => {
  return (
    <div className="p-4 border-t border-gray-800 flex justify-between items-center">
      <div className="text-gray-400">
        Selected: <span className="text-white font-medium">{selectedPlan}</span>
      </div>
      <button
        onClick={onExecute}
        disabled={!canExecute}
        className="px-6 py-2 bg-primary hover:bg-primary/80 disabled:bg-gray-700 disabled:cursor-not-allowed rounded font-medium"
      >
        Execute Plan
      </button>
    </div>
  );
};
```

**Step 3: Commit**

```bash
git add frontend/src/components/optimizer/OptimizerStage.tsx frontend/src/components/optimizer/OptimizerHeader.tsx frontend/src/components/optimizer/PlanCardsPanel.tsx frontend/src/components/optimizer/OptimizerFooter.tsx
git commit -m "feat(component): add OptimizerStage main component with layout"
```

---

## Task 14: Integrate OptimizerStage into PlanView

**Files:**
- Modify: `frontend/src/components/PlanView.tsx`
- Modify: `frontend/src/App.tsx` (add route if needed)

**Step 1: Update PlanView to include optimizer stage**

Open `frontend/src/components/PlanView.tsx`, add new stage:

```typescript
// Import OptimizerStage
import { OptimizerStage } from './optimizer/OptimizerStage';

// In PlanView component, add to stage enum/type
type Stage = 'questions' | 'proposals' | 'optimizer' | 'execution' | 'completed';

// In the render function, add optimizer stage case:
{stage === 'optimizer' && (
  <OptimizerStage
    sessionId={sessionId}
    selectedProposalId={selectedProposalId}
    onComplete={(planId) => {
      // Transition to execution with selected plan
      executePlan(planId);
    }}
    onBack={() => setStage('proposals')}
  />
)}
```

**Step 2: Update proposal selection to go to optimizer**

Find where user selects a proposal, modify to go to optimizer stage:

```typescript
const handleSelectProposal = (proposalId: string) => {
  setSelectedProposalId(proposalId);
  setStage('optimizer'); // Changed from 'execution'
};
```

**Step 3: Test integration**

Run: `cd frontend && npm run dev`
Navigate: Create plan → Answer questions → Select proposal → Should see OptimizerStage

**Step 4: Commit**

```bash
git add frontend/src/components/PlanView.tsx
git commit -m "feat(integration): integrate OptimizerStage into PlanView workflow"
```

---

## Task 15: Demo Mode with Mock Data

**Files:**
- Create: `frontend/src/demo/mockOptimizerData.ts`
- Modify: `frontend/src/components/optimizer/OptimizerStage.tsx` (add demo prop)

**Step 1: Create mock data**

Create `frontend/src/demo/mockOptimizerData.ts`:

```typescript
import { OptimizerState } from '../types/optimizer';

export const mockOptimizerState: OptimizerState = {
  status: 'completed',
  selectedProposalId: 'proposal-mock-123',
  variants: [
    {
      id: 'variant-simplified',
      type: 'simplified',
      name: 'Simplified Plan',
      description: 'Streamlined execution with 30% fewer steps',
      executionGraph: { nodes: [], edges: [] },
      steps: [],
      metadata: {
        stepCount: 7,
        complexityScore: 3.2,
        optimizationNotes: 'Merged user validation steps, combined API calls',
        estimatedCost: 1.80,
        estimatedTime: 12,
      },
    },
    {
      id: 'variant-enhanced',
      type: 'enhanced',
      name: 'Enhanced Plan',
      description: 'Robust execution with validation and error handling',
      executionGraph: { nodes: [], edges: [] },
      steps: [],
      metadata: {
        stepCount: 12,
        complexityScore: 5.8,
        optimizationNotes: 'Added validation checkpoints, rollback mechanisms',
        estimatedCost: 3.20,
        estimatedTime: 18,
      },
    },
    {
      id: 'variant-cost',
      type: 'cost-optimized',
      name: 'Cost-Optimized Plan',
      description: 'Budget-friendly execution with optimized models',
      executionGraph: { nodes: [], edges: [] },
      steps: [],
      metadata: {
        stepCount: 10,
        complexityScore: 4.5,
        optimizationNotes: 'Switched to DeepSeek for steps 1-7, batched operations',
        estimatedCost: 1.50,
        estimatedTime: 15,
      },
    },
  ],
  ratings: [
    {
      planId: 'proposal-mock-123',
      ratings: {
        'claude-3.5-sonnet': {
          modelName: 'claude-3.5-sonnet',
          feasibility: 8.5,
          costEfficiency: 7.0,
          timeEfficiency: 8.0,
          complexity: 6.5,
          overallScore: 7.75,
          reasoning: 'Well-structured with clear dependencies',
        },
        'gpt-4o': {
          modelName: 'gpt-4o',
          feasibility: 8.2,
          costEfficiency: 7.2,
          timeEfficiency: 7.8,
          complexity: 6.8,
          overallScore: 7.75,
          reasoning: 'Solid approach, consider merging steps 3-4',
        },
        'deepseek-v3': {
          modelName: 'deepseek-v3',
          feasibility: 8.0,
          costEfficiency: 7.5,
          timeEfficiency: 7.5,
          complexity: 7.0,
          overallScore: 7.75,
          reasoning: 'Good balance of complexity and efficiency',
        },
      },
      averageScore: 7.75,
      consensus: 0.95,
    },
  ],
  progress: {
    variantsGenerated: 3,
    variantsTotal: 3,
    ratingsCompleted: 9,
    ratingsTotal: 9,
  },
};

export const mockComparisons = [
  {
    planId: 'proposal-mock-123',
    planName: 'Original Proposal',
    planType: 'original' as const,
    metrics: { cost: 2.50, time: 15, feasibility: 8.5, stepCount: 10 },
    aiScores: {
      'claude-3.5-sonnet': 7.75,
      'gpt-4o': 7.75,
      'deepseek-v3': 7.75,
    },
    averageAiScore: 7.75,
  },
  {
    planId: 'variant-simplified',
    planName: 'Simplified Plan',
    planType: 'simplified' as const,
    metrics: { cost: 1.80, time: 12, feasibility: 8.0, stepCount: 7 },
    aiScores: {
      'claude-3.5-sonnet': 8.2,
      'gpt-4o': 8.0,
      'deepseek-v3': 8.5,
    },
    averageAiScore: 8.23,
  },
  {
    planId: 'variant-enhanced',
    planName: 'Enhanced Plan',
    planType: 'enhanced' as const,
    metrics: { cost: 3.20, time: 18, feasibility: 9.1, stepCount: 12 },
    aiScores: {
      'claude-3.5-sonnet': 8.8,
      'gpt-4o': 9.0,
      'deepseek-v3': 8.5,
    },
    averageAiScore: 8.77,
  },
  {
    planId: 'variant-cost',
    planName: 'Cost-Optimized Plan',
    planType: 'cost-optimized' as const,
    metrics: { cost: 1.50, time: 15, feasibility: 7.5, stepCount: 10 },
    aiScores: {
      'claude-3.5-sonnet': 7.0,
      'gpt-4o': 7.2,
      'deepseek-v3': 7.8,
    },
    averageAiScore: 7.33,
  },
];
```

**Step 2: Add demo mode to OptimizerStage**

Modify `frontend/src/components/optimizer/OptimizerStage.tsx`:

```typescript
interface OptimizerStageProps {
  // ... existing props
  demoMode?: boolean;
  mockData?: OptimizerState;
}

export const OptimizerStage: React.FC<OptimizerStageProps> = ({
  sessionId,
  selectedProposalId,
  onComplete,
  onBack,
  demoMode = false,
  mockData,
}) => {
  // Use mock data if demo mode
  const effectiveState = demoMode && mockData ? mockData : state;

  // ... rest of component, use effectiveState instead of state
};
```

**Step 3: Add demo toggle to App**

Add URL param or dev mode toggle:

```typescript
// In App.tsx or a dedicated demo page
const isDemoMode = new URLSearchParams(window.location.search).has('demo');

{isDemoMode && (
  <OptimizerStage
    demoMode
    mockData={mockOptimizerState}
    // ... other props
  />
)}
```

**Step 4: Commit**

```bash
git add frontend/src/demo/mockOptimizerData.ts frontend/src/components/optimizer/OptimizerStage.tsx
git commit -m "feat(demo): add demo mode with mock optimizer data"
```

---

## Task 16: End-to-End Testing

**Files:**
- Create: `frontend/src/tests/e2e/optimizer-flow.test.tsx`
- Create: `backend/tests/integration/test_optimizer_flow.py`

**Step 1: Write frontend E2E test**

Create `frontend/src/tests/e2e/optimizer-flow.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OptimizerStage } from '../../components/optimizer/OptimizerStage';
import { mockOptimizerState } from '../../demo/mockOptimizerData';

describe('Optimizer Flow E2E', () => {
  it('completes full optimizer workflow in demo mode', async () => {
    const onComplete = jest.fn();
    const onBack = jest.fn();

    render(
      <OptimizerStage
        sessionId="test-session"
        selectedProposalId="proposal-123"
        onComplete={onComplete}
        onBack={onBack}
        demoMode
        mockData={mockOptimizerState}
      />
    );

    // Should show completed state immediately in demo mode
    await waitFor(() => {
      expect(screen.getByText('Simplified Plan')).toBeInTheDocument();
      expect(screen.getByText('Enhanced Plan')).toBeInTheDocument();
      expect(screen.getByText('Cost-Optimized Plan')).toBeInTheDocument();
    });

    // Select a plan
    fireEvent.click(screen.getByText('Simplified Plan'));

    // Click execute
    fireEvent.click(screen.getByText('Execute Plan'));

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith('variant-simplified');
    });
  });

  it('shows back button and navigates correctly', async () => {
    const onBack = jest.fn();

    render(
      <OptimizerStage
        sessionId="test-session"
        selectedProposalId="proposal-123"
        onComplete={jest.fn()}
        onBack={onBack}
        demoMode
        mockData={mockOptimizerState}
      />
    );

    fireEvent.click(screen.getByText(/back to proposals/i));

    expect(onBack).toHaveBeenCalled();
  });

  it('displays comparison data correctly', async () => {
    render(
      <OptimizerStage
        sessionId="test-session"
        selectedProposalId="proposal-123"
        onComplete={jest.fn()}
        onBack={jest.fn()}
        demoMode
        mockData={mockOptimizerState}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Comparison Table')).toBeInTheDocument();
      expect(screen.getByText('Radar Chart')).toBeInTheDocument();
      expect(screen.getByText('AI Ratings')).toBeInTheDocument();
    });

    // Switch tabs
    fireEvent.click(screen.getByText('Radar Chart'));
    expect(screen.getByText('Cost Efficiency')).toBeInTheDocument();
  });
});
```

**Step 2: Write backend integration test**

Create `backend/tests/integration/test_optimizer_flow.py`:

```python
import pytest
from backend.services.optimizer_service import OptimizerService


@pytest.mark.asyncio
async def test_full_optimization_flow(db_session, mock_proposal):
    """Test complete flow: optimize → rate → save user rating"""
    service = OptimizerService(db_session)

    # Step 1: Generate variants
    optimization = await service.optimize_proposal(
        proposal_id=mock_proposal.id,
        optimization_types=["simplified", "enhanced"]
    )

    assert optimization["status"] == "completed"
    assert len(optimization["variants"]) == 2

    # Step 2: Rate plans
    plan_ids = [mock_proposal.id, optimization["variants"][0]["id"]]

    ratings = await service.rate_plans(
        session_id=mock_proposal.session_id,
        plan_ids=plan_ids,
        models=["claude-3.5-sonnet"]
    )

    assert ratings["status"] == "completed"
    assert len(ratings["ratings"]) >= 1

    # Step 3: Save user rating
    user_rating = service.save_user_rating(
        session_id=mock_proposal.session_id,
        plan_id=optimization["variants"][0]["id"],
        rating=5,
        comment="Excellent optimization!"
    )

    assert user_rating["saved"] is True
    assert "rating_id" in user_rating


def test_optimization_state_retrieval(db_session, mock_proposal):
    """Test getting optimization state"""
    service = OptimizerService(db_session)

    state = service.get_optimization_state(mock_proposal.session_id)

    assert "status" in state
    assert "progress" in state
    assert "variants_generated" in state["progress"]
```

**Step 3: Run tests**

Frontend: `cd frontend && npm run test:e2e`
Backend: `cd backend && uv run pytest tests/integration/test_optimizer_flow.py -v`

**Step 4: Commit**

```bash
git add frontend/src/tests/e2e/ optimizer-flow.test.tsx backend/tests/integration/test_optimizer_flow.py
git commit -m "test(e2e): add end-to-end optimizer flow tests"
```

---

## Task 17: Documentation

**Files:**
- Create: `frontend/docs/OPTIMIZER_GUIDE.md`
- Create: `backend/docs/OPTIMIZER_API.md`
- Modify: `README.md` (add section about optimizer)

**Step 1: Create user guide**

Create `frontend/docs/OPTIMIZER_GUIDE.md`:

```markdown
# Plan Optimizer Feature Guide

## Overview

The Plan Optimizer helps you find the best execution plan by generating AI-improved variants and gathering ratings from multiple AI models.

## How to Use

### Step 1: Select a Proposal
After reviewing initial proposals, click on your preferred proposal to enter the Optimizer stage.

### Step 2: Generate Optimized Variants
Click "Optimize Plan" to generate 3 alternative versions:
- **Simplified**: Fewer steps, faster execution
- **Enhanced**: More validation and error handling
- **Cost-Optimized**: Lower cost using efficient models

### Step 3: Review AI Ratings
Multiple AI models (Claude, GPT-4o, DeepSeek) rate each plan on:
- Feasibility (1-10)
- Cost Efficiency (1-10)
- Time Efficiency (1-10)
- Complexity (1-10)

### Step 4: Compare Plans
Use the comparison table or radar chart to visualize trade-offs between plans.

### Step 5: Add Your Rating
Share your expertise by rating plans and adding comments about your choice.

### Step 6: Execute
Select the best plan and click "Execute Plan" to begin execution.

## Understanding the Display

### Color Coding
- **Blue**: Original proposal
- **Green**: Simplified variant
- **Purple**: Enhanced variant
- **Amber**: Cost-optimized variant

### Metrics
- **Cost**: Estimated execution cost in USD
- **Time**: Estimated execution time in minutes
- **Feasibility**: AI confidence in plan success
- **Steps**: Number of execution steps

### AI Consensus
When models agree, you'll see a green checkmark. Disagreements are shown with an amber indicator - this means the plan has trade-offs.
```

**Step 2: Create API documentation**

Create `backend/docs/OPTIMIZER_API.md`:

```markdown
# Optimizer API Documentation

## Endpoints

### POST /api/v1/sessions/{session_id}/optimize

Generate optimized variants of a selected proposal.

**Request:**
```json
{
  "selected_proposal_id": "uuid",
  "optimization_types": ["simplified", "enhanced", "cost-optimized"]
}
```

**Response:**
```json
{
  "optimization_id": "uuid",
  "status": "completed",
  "variants": [...]
}
```

### POST /api/v1/sessions/{session_id}/rate

Rate plans using multiple AI models.

**Request:**
```json
{
  "plan_ids": ["uuid1", "uuid2"],
  "models": ["claude-3.5-sonnet", "gpt-4o", "deepseek-v3"],
  "criteria": ["feasibility", "cost_efficiency", "time_efficiency", "complexity"]
}
```

**Response:**
```json
{
  "rating_id": "uuid",
  "status": "completed",
  "ratings": {...}
}
```

### POST /api/v1/sessions/{session_id}/user-rating

Save user's rating for a plan.

**Request:**
```json
{
  "plan_id": "uuid",
  "rating": 5,
  "comment": "Optional comment",
  "rationale": "Optional rationale"
}
```

### GET /api/v1/sessions/{session_id}/optimization-state

Get current optimization progress.

**Response:**
```json
{
  "status": "generating_variants",
  "phase": "variant_generation",
  "progress": {
    "variants_generated": 2,
    "variants_total": 3
  }
}
```

### SSE: /api/v1/sessions/{session_id}/optimization-stream

Server-Sent Events stream for real-time updates.

**Events:**
- `variant_generated`: New variant available
- `model_rated`: Model finished rating
- `ratings_complete`: All ratings complete
```

**Step 3: Update main README**

Open `README.md`, add section:

```markdown
## Plan Optimizer

The Plan Optimizer is an advanced feature that generates AI-improved variants of your selected plan and provides multi-model AI ratings to help you choose the best execution path.

### Features

- **3 Variant Types**: Simplified, Enhanced, and Cost-optimized plans
- **Multi-Model Rating**: Get ratings from Claude 3.5 Sonnet, GPT-4o, and DeepSeek V3
- **Visual Comparison**: Table and radar chart views for easy comparison
- **User Input**: Add your own ratings and comments
- **Real-time Updates**: Watch optimization progress via SSE

### Usage

1. Select a proposal from the proposal list
2. Click "Optimize Plan" to generate variants
3. Review AI ratings and comparisons
4. Select the best plan
5. Click "Execute Plan" to begin execution

See [frontend/docs/OPTIMIZER_GUIDE.md](frontend/docs/OPTIMIZER_GUIDE.md) for detailed usage instructions.
```

**Step 4: Commit**

```bash
git add frontend/docs/OPTIMIZER_GUIDE.md backend/docs/OPTIMIZER_API.md README.md
git commit -m "docs: add optimizer feature documentation"
```

---

## Task 18: Performance & Load Testing

**Files:**
- Create: `backend/tests/performance/test_optimizer_performance.py`
- Modify: `backend/services/optimizer_service.py` (add caching if needed)

**Step 1: Write performance tests**

Create `backend/tests/performance/test_optimizer_performance.py`:

```python
import pytest
import time
from backend.services.optimizer_service import OptimizerService


@pytest.mark.asyncio
@pytest.mark.performance
async def test_variant_generation_performance(db_session, mock_proposal):
    """Test that variant generation completes within 15 seconds"""
    service = OptimizerService(db_session)

    start = time.time()
    result = await service.optimize_proposal(
        proposal_id=mock_proposal.id,
        optimization_types=["simplified", "enhanced", "cost-optimized"]
    )
    duration = time.time() - start

    assert result["status"] == "completed"
    assert duration < 15, f"Variant generation took {duration}s, expected < 15s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_rating_performance(db_session, mock_proposal):
    """Test that multi-model rating completes within 45 seconds"""
    service = OptimizerService(db_session)

    # Generate variants first
    optimization = await service.optimize_proposal(proposal_id=mock_proposal.id)
    plan_ids = [mock_proposal.id, optimization["variants"][0]["id"]]

    start = time.time()
    result = await service.rate_plans(
        session_id=mock_proposal.session_id,
        plan_ids=plan_ids,
        models=["claude-3.5-sonnet", "gpt-4o", "deepseek-v3"]
    )
    duration = time.time() - start

    assert result["status"] == "completed"
    assert duration < 45, f"Rating took {duration}s, expected < 45s"
```

**Step 2: Run performance tests**

Run: `cd backend && uv run pytest -m performance tests/performance/ -v`

**Step 3: Add caching if needed**

If tests show slow performance, add caching to `backend/services/optimizer_service.py`:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def _build_rating_prompt_cached(plan_graph: str, criteria: tuple) -> str:
    """Cache rating prompt construction"""
    return RATING_PROMPT.format(
        plan_graph=plan_graph,
        criteria=", ".join(criteria)
    )
```

**Step 4: Commit**

```bash
git add backend/tests/performance/test_optimizer_performance.py
git commit -m "test(perf): add optimizer performance tests"
```

---

## Task 19: Security & Validation Audit

**Files:**
- Create: `backend/tests/security/test_optimizer_security.py`
- Modify: `backend/routes/optimizer_routes.py` (add rate limiting if missing)

**Step 1: Write security tests**

Create `backend/tests/security/test_optimizer_security.py`:

```python
import pytest
from fastapi.testclient import TestClient


def test_optimize_requires_auth(client, db_session):
    """Test that optimization endpoint requires authentication"""
    response = client.post(
        "/api/v1/sessions/session-123/optimize",
        json={"selected_proposal_id": "prop-123"}
    )

    assert response.status_code == 401  # Unauthorized


def test_invalid_proposal_id_rejected(client, db_session, auth_token):
    """Test that invalid proposal IDs are rejected"""
    response = client.post(
        "/api/v1/sessions/session-123/optimize",
        json={"selected_proposal_id": "too-short"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 422  # Validation error


def test_rating_range_validation(client, db_session, auth_token):
    """Test that ratings must be between 1 and 5"""
    response = client.post(
        "/api/v1/sessions/session-123/user-rating",
        json={
            "plan_id": "plan-123",
            "rating": 6  # Invalid
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 422


def test_rate_limiting(client, db_session, auth_token):
    """Test that optimization endpoint is rate limited"""
    # Make 11 requests (limit is 10 per minute)
    responses = []
    for i in range(11):
        response = client.post(
            "/api/v1/sessions/session-123/optimize",
            json={"selected_proposal_id": f"prop-{i}"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        responses.append(response)

    # At least one should be rate limited
    assert any(r.status_code == 429 for r in responses)
```

**Step 2: Add rate limiting middleware**

Open `backend/routes/optimizer_routes.py`, ensure rate limiting is applied:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/optimize")
@limiter.limit("10/minute")
async def optimize_proposal(...):
    # ... existing code
```

**Step 3: Run security tests**

Run: `cd backend && uv run pytest tests/security/test_optimizer_security.py -v`

**Step 4: Commit**

```bash
git add backend/tests/security/test_optimizer_security.py backend/routes/optimizer_routes.py
git commit -m "test(security): add optimizer security tests and rate limiting"
```

---

## Task 20: Final Integration & Smoke Tests

**Files:**
- Create: `backend/tests/smoke/test_full_optimizer_smoke.py`
- Create: `frontend/src/tests/smoke/optimizer-smoke.test.tsx`

**Step 1: Write backend smoke test**

Create `backend/tests/smoke/test_full_optimizer_smoke.py`:

```python
import pytest


@pytest.mark.smoke
def test_optimizer_module_imports():
    """Test that all optimizer modules can be imported"""
    from backend.services.optimizer_service import OptimizerService
    from backend.services.variant_generator import VariantGenerator
    from backend.services.model_rater import ModelRater
    from backend.routes.optimizer_routes import router
    from backend.models.optimized_variant import OptimizedVariant
    from backend.models.plan_rating import PlanRating
    from backend.models.user_rating import UserRating

    assert OptimizerService is not None
    assert VariantGenerator is not None
    assert ModelRater is not None
    assert router is not None


@pytest.mark.smoke
def test_optimizer_routes_registered(client):
    """Test that optimizer routes are registered"""
    response = client.options("/api/v1/sessions/test-123/optimize")
    # Should not 404 (might 401 due to auth, which is fine)
    assert response.status_code != 404
```

**Step 2: Write frontend smoke test**

Create `frontend/src/tests/smoke/optimizer-smoke.test.tsx`:

```typescript
describe('Optimizer Smoke Tests', () => {
  it('imports all optimizer components', () => {
    expect(() => {
      require('../../components/optimizer/OptimizerStage');
      require('../../components/optimizer/ComparisonPanel');
      require('../../components/optimizer/PlanCard');
      require('../../hooks/useOptimizer');
      require('../../hooks/useOptimizerSSE');
    }).not.toThrow();
  });

  it('renders OptimizerStage without crashing', () => {
    const { container } = render(
      <OptimizerStage
        sessionId="test"
        selectedProposalId="prop-123"
        onComplete={jest.fn()}
        onBack={jest.fn()}
        demoMode
        mockData={mockOptimizerState}
      />
    );
    expect(container).toBeInTheDocument();
  });
});
```

**Step 3: Run all smoke tests**

Backend: `cd backend && uv run pytest -m smoke -v`
Frontend: `cd frontend && npm run test -- --testNamePattern="smoke"`

**Step 4: Run full test suite**

Backend: `cd backend && uv run pytest -v`
Frontend: `cd frontend && npm test`

**Step 5: Manual smoke test**

1. Start backend: `cd backend && uv run uvicorn backend.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to http://localhost:5173
4. Create a new plan
5. Answer questions
6. Select a proposal
7. Should see Optimizer stage
8. Click "Optimize Plan"
9. Wait for variants and ratings
10. Compare plans in table and radar chart
11. Add user rating
12. Select a plan
13. Click "Execute Plan"
14. Should proceed to execution

**Step 6: Commit**

```bash
git add backend/tests/smoke/ frontend/src/tests/smoke/
git commit -m "test(smoke): add smoke tests for optimizer feature"
```

---

## Task 21: Cleanup & Final Polish

**Step 1: Remove console.logs and debug statements**

Search and remove any `console.log` statements added during development:

```bash
# Frontend
cd frontend
grep -r "console.log" src/components/optimizer/ src/hooks/
# Remove or comment out debug logs

# Backend
cd backend
grep -r "print(" services/optimizer*.py services/variant*.py services/model*.py
# Remove or convert to proper logging
```

**Step 2: Add proper logging**

Update backend services to use proper logging:

```python
import logging

logger = logging.getLogger(__name__)

# In methods:
logger.info(f"Generating {len(optimization_types)} variants for proposal {proposal_id}")
logger.warning(f"Model {model} failed to rate plan {plan_id}")
```

**Step 3: Check for TODO comments**

```bash
# Find and address TODOs
grep -r "TODO" frontend/src/components/optimizer/ backend/services/
```

**Step 4: Format code**

```bash
# Backend
cd backend
uv run ruff check .
uv run ruff format .

# Frontend
cd frontend
npm run format
npm run lint
```

**Step 5: Update package.json dependencies**

Check for any new dependencies added:

```bash
cd frontend
npm install
cd ../backend
uv sync
```

**Step 6: Create final demo script**

Create `demo-optimizer.sh`:

```bash
#!/bin/bash

echo "🚀 Starting PlanWeaver Optimizer Demo"
echo ""
echo "1. Starting backend..."
cd backend
uv run uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "2. Starting frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Demo started!"
echo "   Frontend: http://localhost:5173?demo=true"
echo "   Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

wait
```

Make executable: `chmod +x demo-optimizer.sh`

**Step 7: Final commit**

```bash
git add .
git commit -m "chore: final cleanup and polish for optimizer feature"
```

**Step 8: Create release tag**

```bash
git tag -a v0.2.0-optimizer -m "Release Plan Optimizer feature"
git push origin main --tags
```

---

## Summary

This implementation plan covers:

✅ **Backend (Tasks 1-8)**: Database models, services, API routes, SSE
✅ **Frontend (Tasks 9-14)**: Types, hooks, components, integration
✅ **Demo Support (Task 15)**: Mock data for presentations
✅ **Testing (Tasks 16, 18-21)**: Unit, integration, E2E, performance, security, smoke
✅ **Documentation (Task 17)**: User guide, API docs, README updates
✅ **Quality (Task 21)**: Cleanup, formatting, logging

**Estimated Timeline**: 3-5 days for full implementation

**Testing Coverage Goal**: >80% for new code

**Demo Ready**: Task 15 enables offline demos without API dependencies

---

## Next Steps After Implementation

1. **User Testing**: Gather feedback on optimizer UI/UX
2. **Metrics**: Track which variant types users prefer
3. **A/B Testing**: Test different optimization strategies
4. **Model Fine-tuning**: Improve variant quality based on user ratings
5. **Performance**: Monitor costs and optimize LLM usage
6. **Documentation**: Create video tutorials for the optimizer feature
