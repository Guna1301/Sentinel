
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update

from db.database import AsyncSessionLocal
from db.schema import monitoring_configs


async def get_due_monitoring_configs(
    *,
    now: datetime,
    limit: int = 100,
) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                monitoring_configs.c.id,
                monitoring_configs.c.interval_seconds,
                monitoring_configs.c.next_check_at,
            )
            .where(
                monitoring_configs.c.enabled.is_(True),
                monitoring_configs.c.next_check_at <= now,
            )
            .order_by(monitoring_configs.c.next_check_at.asc())
            .limit(limit)
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


async def advance_monitoring_schedule(
    *,
    config_id: UUID,
    expected_next_check_at: datetime,
    next_check_at: datetime,
) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(monitoring_configs)
            .where(
                monitoring_configs.c.id == config_id,
                monitoring_configs.c.enabled.is_(True),
                monitoring_configs.c.next_check_at
                == expected_next_check_at,
            )
            .values(
                next_check_at=next_check_at,
            )
        )

        await session.commit()

        return result.rowcount == 1
