
import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class HttpCheckResult:
    success: bool
    status_code: int | None
    latency_ms: int
    error: str | None


class HttpCheckClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def check(
        self,
        *,
        url: str,
        method: str,
        timeout_seconds: int,
    ) -> HttpCheckResult:
        started_at = time.perf_counter()

        try:
            response = await self._client.request(
                method=method,
                url=url,
                timeout=timeout_seconds,
            )
        except httpx.RequestError as exc:
            return HttpCheckResult(
                success=False,
                status_code=None,
                latency_ms=self._calculate_latency(started_at),
                error=self._format_error(exc),
            )

        return HttpCheckResult(
            success=200 <= response.status_code < 400,
            status_code=response.status_code,
            latency_ms=self._calculate_latency(started_at),
            error=None,
        )

    @staticmethod
    def _calculate_latency(started_at: float) -> int:
        return max(
            0,
            round((time.perf_counter() - started_at) * 1000),
        )

    @staticmethod
    def _format_error(exc: httpx.RequestError) -> str:
        return f"{type(exc).__name__}: {exc}"[:2048]
