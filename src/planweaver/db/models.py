from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey
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
