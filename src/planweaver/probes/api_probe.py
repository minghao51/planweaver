"""
API reachability probe.
"""

import asyncio
import aiohttp
from .base import Probe, ProbeResult


class ApiProbe(Probe):
    """Probe for checking if an API endpoint is reachable."""

    async def check(self, expression: str) -> ProbeResult:
        url = expression.strip()
        if not url.startswith(("http://", "https://")):
            return self._error_result(f"Invalid URL: {url}")

        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.head(url) as response:
                    return ProbeResult(success=True, result=response.status < 500)
        except asyncio.TimeoutError:
            return ProbeResult(success=True, result=False)
        except Exception as e:
            return self._error_result(f"API check failed: {e}")
