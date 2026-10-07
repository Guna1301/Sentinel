import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import insert, select

from db.database import AsyncSessionLocal
from db.schema import monitor_checks, monitoring_configs


async def get_monitoring_config(
    config_id: UUID,
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                monitoring_configs.c.id,
                monitoring_configs.c.url,
                monitoring_configs.c.method,
                monitoring_configs.c.timeout_seconds,
                monitoring_configs.c.enabled,
            ).where(
                monitoring_configs.c.id == config_id,
            )
        )

        return result.mappings().one_or_none()


async def create_monitor_check(
    *,
    monitoring_config_id: UUID,
    checked_at: datetime,
    success: bool,
    status_code: int | None,
    latency_ms: int | None,
    error: str | None,
) -> UUID:
    check_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        await session.execute(
            insert(monitor_checks).values(
                id=check_id,
                monitoring_config_id=monitoring_config_id,
                checked_at=checked_at,
                success=success,
                status_code=status_code,
                latency_ms=latency_ms,
                error=error,
            )
        )

        await session.commit()

    return check_id