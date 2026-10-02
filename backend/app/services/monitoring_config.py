from uuid import UUID

from app.models.monitoring_config import MonitoringConfig
from app.repositories.monitoring_config import MonitoringConfigRepository


class MonitoringConfigService:
    def __init__(
        self,
        repository: MonitoringConfigRepository,
    ):
        self._repository = repository

    async def create_config(
        self,
        service_id: UUID,
        project_id: UUID,
        owner_id: UUID,
        url: str,
        method: str,
        interval_seconds: int,
        timeout_seconds: int,
        enabled: bool,
    ) -> MonitoringConfig | None:
        service_exists = await self._repository.service_belongs_to_owner(
            service_id=service_id,
            project_id=project_id,
            owner_id=owner_id,
        )

        if not service_exists:
            return None

        return await self._repository.create(
            service_id=service_id,
            url=url,
            method=method,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            enabled=enabled,
        )

    async def get_config(
        self,
        service_id: UUID,
        project_id: UUID,
        owner_id: UUID,
    ) -> MonitoringConfig | None:
        return await self._repository.get_by_service_for_owner(
            service_id=service_id,
            project_id=project_id,
            owner_id=owner_id,
        )

    async def update_config(self, config: MonitoringConfig, **updates) -> MonitoringConfig:
        for field, value in updates.items():
            if field == "url":
                value = str(value)

            setattr(config, field, value)

        return config

    async def delete_config(
        self,
        config: MonitoringConfig,
    ) -> None:
        await self._repository.delete(config)