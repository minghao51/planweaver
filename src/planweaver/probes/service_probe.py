"""
Service running probe.
"""

import asyncio
from .base import Probe, ProbeResult


class ServiceProbe(Probe):
    """Probe for checking if a service is running (TCP port check)."""

    async def check(self, expression: str) -> ProbeResult:
        try:
            parts = expression.strip().rsplit(":", 1)
            if len(parts) != 2:
                return self._error_result(f"Invalid service expression: {expression}. Expected 'host:port'")
            host, port_str = parts
            try:
                port = int(port_str)
            except ValueError:
                return self._error_result(f"Invalid port: {port_str}")

            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=5.0,
                )
                writer.close()
                await writer.wait_closed()
                return ProbeResult(success=True, result=True)
            except (ConnectionRefusedError, ConnectionResetError, OSError):
                return ProbeResult(success=True, result=False)
            except asyncio.TimeoutError:
                return ProbeResult(success=True, result=False)
        except Exception as e:
            return self._error_result(f"Service check failed: {e}")
