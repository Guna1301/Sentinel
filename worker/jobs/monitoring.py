from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from db.monitoring import (
    create_monitor_check,
    get_monitoring_config,
)


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

    # Record when this check begins.
    checked_at = datetime.now(timezone.utc)

    http_client = ctx["http_check_client"]

    result = await http_client.check(
        url=config["url"],
        method=config["method"],
        timeout_seconds=config["timeout_seconds"],
    )

    check_id = await create_monitor_check(
        monitoring_config_id=config["id"],
        checked_at=checked_at,
        success=result.success,
        status_code=result.status_code,
        latency_ms=result.latency_ms,
        error=result.error,
    )

    return {
        "status": "completed",
        "check_id": str(check_id),
        "success": result.success,
    }