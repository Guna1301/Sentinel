
from typing import Any
from uuid import UUID

from db.incidents import persist_check_and_evaluate_incident
from db.monitoring import get_monitoring_config


async def check_monitor(
    ctx: dict[str, Any],
    monitoring_config_id: str,
) -> dict[str, str | bool]:
    config_id = UUID(monitoring_config_id)

    config = await get_monitoring_config(config_id)

    if config is None:
        return {
            "status": "skipped",
            "reason": "config_not_found",
        }

    if not config["enabled"]:
        return {
            "status": "skipped",
            "reason": "config_disabled",
        }

    http_client = ctx["http_check_client"]

    result = await http_client.check(
        url=config["url"],
        method=config["method"],
        timeout_seconds=config["timeout_seconds"],
    )

    persistence = await persist_check_and_evaluate_incident(
        monitoring_config_id=config["id"],
        success=result.success,
        status_code=result.status_code,
        latency_ms=result.latency_ms,
        error=result.error,
    )

    if persistence is None:
        return {
            "status": "skipped",
            "reason": "config_not_found",
        }

    check_id, decision = persistence

    return {
        "status": "completed",
        "check_id": str(check_id),
        "success": result.success,
        "incident_action": decision.action,
    }
