from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitor_check import MonitorCheck

from sqlalchemy import func, select

class MonitorCheckRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_latest_for_config(
        self,
        monitoring_config_id: UUID,
    ) -> MonitorCheck | None:
        result = await self._session.execute(
            select(MonitorCheck)
            .where(
                MonitorCheck.monitoring_config_id
                == monitoring_config_id
            )
            .order_by(
                MonitorCheck.checked_at.desc(),
                MonitorCheck.id.desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()


    async def list_for_config(
        self,
        monitoring_config_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[MonitorCheck]:
        result = await self._session.execute(
            select(MonitorCheck)
            .where(
                MonitorCheck.monitoring_config_id
                == monitoring_config_id
            )
            .order_by(
                MonitorCheck.checked_at.desc(),
                MonitorCheck.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all())


    async def count_for_config(
        self,
        monitoring_config_id: UUID,
    ) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(MonitorCheck)
            .where(
                MonitorCheck.monitoring_config_id
                == monitoring_config_id
            )
        )

        return result.scalar_one()