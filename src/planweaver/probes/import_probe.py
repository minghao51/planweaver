"""
Import availability probe.
"""

import importlib
from .base import Probe, ProbeResult


class ImportProbe(Probe):
    """Probe for checking if a Python module or library is importable."""

    async def check(self, expression: str) -> ProbeResult:
        module_name = expression.strip()
        try:
            importlib.import_module(module_name)
            return ProbeResult(success=True, result=True)
        except ImportError:
            return ProbeResult(success=True, result=False)
        except Exception as e:
            return self._error_result(f"Import check failed: {e}")
