
import httpx
import pytest

from clients.http import HttpCheckClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_success"),
    [
        (200, True),
        (204, True),
        (301, True),
        (399, True),
        (400, False),
        (404, False),
        (500, False),
        (503, False),
    ],
)
async def test_status_code_mapping(
    status_code: int,
    expected_success: bool,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
    ) as client:
        result = await HttpCheckClient(client).check(
            url="https://example.com/health",
            method="GET",
            timeout_seconds=5,
        )

    assert result.success is expected_success
    assert result.status_code == status_code
    assert result.latency_ms >= 0
    assert result.error is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error_type", "message"),
    [
        (httpx.ConnectTimeout, "request timed out"),
        (httpx.ConnectError, "connection refused"),
    ],
)
async def test_request_errors_become_failed_results(
    error_type: type[httpx.RequestError],
    message: str,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise error_type(message, request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await HttpCheckClient(client).check(
            url="https://example.com/health",
            method="GET",
            timeout_seconds=5,
        )

    assert result.success is False
    assert result.status_code is None
    assert result.latency_ms >= 0
    assert error_type.__name__ in result.error
    assert message in result.error


@pytest.mark.asyncio
async def test_method_and_url_are_forwarded() -> None:
    observed: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        observed["method"] = request.method
        observed["url"] = str(request.url)
        return httpx.Response(200, request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await HttpCheckClient(client).check(
            url="https://example.com/api/health",
            method="HEAD",
            timeout_seconds=7,
        )

    assert result.success is True
    assert observed == {
        "method": "HEAD",
        "url": "https://example.com/api/health",
    }


@pytest.mark.asyncio
async def test_unexpected_errors_propagate() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise RuntimeError("unexpected programming error")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as client:
        check_client = HttpCheckClient(client)

        with pytest.raises(
            RuntimeError,
            match="unexpected programming error",
        ):
            await check_client.check(
                url="https://example.com/health",
                method="GET",
                timeout_seconds=5,
            )
