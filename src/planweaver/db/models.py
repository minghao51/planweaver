from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
import enum
import uuid

Base = declarative_base()


class PlanStatusDB(str, enum.Enum):
    BRAINSTORMING = "BRAINSTORMING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepStatusDB(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    user_intent = Column(Text, nullable=False)
    scenario_name = Column(String(255), nullable=True)
    status = Column(String(50), default=PlanStatusDB.BRAINSTORMING.value)
    locked_constraints = Column(JSON, default=dict)
    open_questions = Column(JSON, default=list)
    strawman_proposals = Column(JSON, default=list)
    execution_graph = Column(JSON, default=list)
    external_contexts = Column(JSON, default=list)
    final_output = Column(JSON, nullable=True)


class PlanModel(Base):
    __tablename__ = "plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    status = Column(String(50), default=PlanStatusDB.BRAINSTORMING.value)
    locked_constraints = Column(JSON, default=dict)
    execution_graph = Column(JSON, default=list)
    final_output = Column(JSON, nullable=True)


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    step_id = Column(Integer, nullable=False)
    step_task = Column(Text, nullable=False)
    model_used = Column(String(255), nullable=False)
    prompt_sent = Column(Text, nullable=False)
    response_received = Column(Text, nullable=True)
    status = Column(String(50), default=StepStatusDB.PENDING.value)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AvailableModel(Base):
    __tablename__ = "available_models"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # 'planner', 'executor', or 'both'
    is_free = Column(Boolean, default=True, nullable=False)
    pricing_info = Column(JSON, nullable=True)
    context_length = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class OptimizedVariant(Base):
    __tablename__ = "optimized_variants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    proposal_id = Column(String(36), nullable=False, index=True)
    variant_type = Column(String(50), nullable=False)  # 'simplified', 'enhanced', 'cost-optimized'
    execution_graph = Column(JSON, nullable=False)
    variant_metadata = Column(JSON, nullable=True)  # {step_count, complexity_score, optimization_notes, etc}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class PlanRating(Base):
    __tablename__ = "plan_ratings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    plan_id = Column(String(36), nullable=False, index=True)  # Can be proposal or variant ID
    model_name = Column(String(100), nullable=False, index=True)  # 'claude-3.5-sonnet', 'gpt-4o', etc
    ratings = Column(JSON, nullable=False)  # {feasibility: 8.5, cost_efficiency: 7.0, ...}
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class UserRating(Base):
    __tablename__ = "user_ratings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    plan_id = Column(String(36), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
