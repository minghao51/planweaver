"""Data models for multi-agent coordination patterns"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime, timezone


class PlanningMode(str, Enum):
    """Planning pattern modes for multi-agent coordination"""

    BASELINE = "baseline"
    SPECIALIST = "specialist"
    ENSEMBLE = "ensemble"
    DEBATE = "debate"


class SubPlanFragment(BaseModel):
    """Partial DAG from a domain specialist"""

    fragment_id: str
    domain: str
    specialist: str
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="ExecutionStep serialized")
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DebateRound(BaseModel):
    """Single round of debate"""

    round_id: str
    decision_point: str
    proposer_argument: str
    opposer_argument: str
    synthesizer_decision: str
    selected_approach: str
    rationale: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
