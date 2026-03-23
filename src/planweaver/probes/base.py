"""
Base probe interface for precondition validation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProbeResult:
    success: bool
    result: Optional[bool]
    error: Optional[str] = None


class Probe(ABC):
    """Abstract base class for precondition probes."""

    @abstractmethod
    async def check(self, expression: str) -> ProbeResult:
        """Check the precondition against the given expression."""
        pass

    def _error_result(self, error: str) -> ProbeResult:
        return ProbeResult(success=False, result=None, error=error)
