from datetime import datetime
from uuid import UUID

import pytest

import jobs.monitoring as monitoring_job
from clients.http import HttpCheckResult
from services.incidents import IncidentDecision


CONFIG_ID = UUID("11111111-1111-4111-8111-111111111111")
CHECK_ID = UUID("22222222-2222-4222-8222-222222222222")

CONFIG = {
    "id": CONFIG_ID,
    "url": "https://example.com/health",
    "method": "GET",
    "timeout_seconds": 5,
    "enabled": True,
}


class FakeHttpCheckClient:
    def __init__(self, result: HttpCheckResult):
        self.result = result
        self.calls = []

    async def check(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "http_result",
    [
        HttpCheckResult(
            success=True,
            status_code=200,
            latency_ms=24,
            error=None,
        ),
        HttpCheckResult(
            success=False,
            status_code=503,
            latency_ms=51,
            error=None,
        ),
    ],
)
async def test_check_monitor_persists_http_result(
    monkeypatch,
    http_result,
):
    persisted_checks = []

    async def fake_get_config(config_id):
        assert config_id == CONFIG_ID
        return CONFIG

    monkeypatch.setattr(
        monitoring_job,
        "get_monitoring_config",
        fake_get_config,
    )

    async def fake_persist(**kwargs):
        persisted_checks.append(kwargs)
        return (
            CHECK_ID,
            IncidentDecision(
                action="none",
                reason="test_no_transition",
            ),
        )

    monkeypatch.setattr(
        monitoring_job,
        "persist_check_and_evaluate_incident",
        fake_persist,
    )


    http_client = FakeHttpCheckClient(http_result)

    result = await monitoring_job.check_monitor(
        {"http_check_client": http_client},
        str(CONFIG_ID),
    )

    assert result == {
        "status": "completed",
        "check_id": str(CHECK_ID),
        "success": http_result.success,
        "incident_action": "none",
    }

    assert http_client.calls == [
        {
            "url": CONFIG["url"],
            "method": CONFIG["method"],
            "timeout_seconds": CONFIG["timeout_seconds"],
        }
    ]

    assert len(persisted_checks) == 1

    check = persisted_checks[0]

    assert persisted_checks == [
        {
            "monitoring_config_id": CONFIG_ID,
            "success": http_result.success,
            "status_code": http_result.status_code,
            "latency_ms": http_result.latency_ms,
            "error": http_result.error,
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("config", "expected_reason"),
    [
        (None, "config_not_found"),
        ({**CONFIG, "enabled": False}, "config_disabled"),
    ],
)
async def test_check_monitor_skips_missing_or_disabled_config(
    monkeypatch,
    config,
    expected_reason,
):
    async def fake_get_config(config_id):
        assert config_id == CONFIG_ID
        return config

    async def unexpected_persist(**kwargs):
        pytest.fail("A skipped check must not be persisted")

    monkeypatch.setattr(
        monitoring_job,
        "get_monitoring_config",
        fake_get_config,
    )
    monkeypatch.setattr(
        monitoring_job,
        "persist_check_and_evaluate_incident",
        unexpected_persist,
    )

    http_client = FakeHttpCheckClient(
        HttpCheckResult(True, 200, 10, None)
    )

    result = await monitoring_job.check_monitor(
        {"http_check_client": http_client},
        str(CONFIG_ID),
    )

    assert result == {
        "status": "skipped",
        "reason": expected_reason,
    }
    assert http_client.calls == []