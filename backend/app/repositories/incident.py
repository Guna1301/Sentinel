from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident


class IncidentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_for_config(
        self,
        monitoring_config_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[Incident]:
        result = await self._session.execute(
            select(Incident)
            .where(
                Incident.monitoring_config_id == monitoring_config_id
            )
            .order_by(
                Incident.opened_at.desc(),
                Incident.id.desc(),
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
            .select_from(Incident)
            .where(
                Incident.monitoring_config_id == monitoring_config_id
            )
        )

        return result.scalar_one()

    async def get_by_id_for_config(
        self,
        incident_id: UUID,
        monitoring_config_id: UUID,
    ) -> Incident | None:
        result = await self._session.execute(
            select(Incident).where(
                Incident.id == incident_id,
                Incident.monitoring_config_id == monitoring_config_id,
            )
        )

        return result.scalar_one_or_none()