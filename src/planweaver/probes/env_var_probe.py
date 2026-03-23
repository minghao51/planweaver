"""
Environment variable probe.
"""

import os
from .base import Probe, ProbeResult


class EnvVarProbe(Probe):
    """Probe for checking if an environment variable is set."""

    async def check(self, expression: str) -> ProbeResult:
        var_name = expression.strip()
        value = os.environ.get(var_name)
        return ProbeResult(success=True, result=value is not None)
