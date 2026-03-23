"""
Precondition probes for Scout agent.

Each probe validates a specific precondition type before execution.
"""

from .base import Probe, ProbeResult
from .file_probe import FileProbe
from .api_probe import ApiProbe
from .import_probe import ImportProbe
from .env_var_probe import EnvVarProbe
from .service_probe import ServiceProbe

PRECONDITION_TYPE_TO_PROBE = {
    "file_exists": FileProbe(),
    "api_reachable": ApiProbe(),
    "import_available": ImportProbe(),
    "env_var_set": EnvVarProbe(),
    "service_running": ServiceProbe(),
}


async def run_probe(precondition_type: str, check_expression: str) -> ProbeResult:
    """Run the appropriate probe for the given precondition type."""
    probe = PRECONDITION_TYPE_TO_PROBE.get(precondition_type)
    if not probe:
        return ProbeResult(
            success=False,
            result=None,
            error=f"Unknown precondition type: {precondition_type}",
        )
    return await probe.check(check_expression)


__all__ = [
    "Probe",
    "ProbeResult",
    "FileProbe",
    "ApiProbe",
    "ImportProbe",
    "EnvVarProbe",
    "ServiceProbe",
    "run_probe",
    "PRECONDITION_TYPE_TO_PROBE",
]
