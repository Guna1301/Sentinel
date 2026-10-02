from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring_config import MonitoringConfig
from app.models.project import Project
from app.models.service import Service


class MonitoringConfigRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def service_belongs_to_owner(
        self,
        service_id: UUID,
        project_id: UUID,
        owner_id: UUID,
    ) -> bool:
        result = await self._session.execute(
            select(Service.id)
            .join(Project, Project.id == Service.project_id)
            .where(
                Service.id == service_id,
                Service.project_id == project_id,
                Project.owner_id == owner_id,
            )
        )

        return result.scalar_one_or_none() is not None

    async def create(
        self,
        service_id: UUID,
        url: str,
        method: str,
        interval_seconds: int,
        timeout_seconds: int,
        enabled: bool,
    ) -> MonitoringConfig:
        config = MonitoringConfig(
            service_id=service_id,
            url=url,
            method=method,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            enabled=enabled,
        )

        self._session.add(config)
        await self._session.flush()

        return config

    async def get_by_service_for_owner(
        self,
        service_id: UUID,
        project_id: UUID,
        owner_id: UUID,
    ) -> MonitoringConfig | None:
        result = await self._session.execute(
            select(MonitoringConfig)
            .join(Service, Service.id == MonitoringConfig.service_id)
            .join(Project, Project.id == Service.project_id)
            .where(
                MonitoringConfig.service_id == service_id,
                Service.project_id == project_id,
                Project.owner_id == owner_id,
            )
        )

        return result.scalar_one_or_none()

    async def delete(
        self,
        config: MonitoringConfig,
    ) -> None:
        await self._session.delete(config)
        await self._session.flush()