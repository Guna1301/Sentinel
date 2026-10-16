from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitor_check import MonitorCheck


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