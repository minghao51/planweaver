"""
File existence probe.
"""

from pathlib import Path
from .base import Probe, ProbeResult


class FileProbe(Probe):
    """Probe for checking if a file exists."""

    async def check(self, expression: str) -> ProbeResult:
        try:
            path = Path(expression.strip())
            if path.exists():
                return ProbeResult(success=True, result=True)
            return ProbeResult(success=True, result=False)
        except Exception as e:
            return self._error_result(f"File check failed: {e}")
