from uuid import UUID

from app.models.monitor_check import MonitorCheck
from app.repositories.monitor_check import MonitorCheckRepository
from app.repositories.monitoring_config import (
    MonitoringConfigRepository,
)


class MonitorCheckService:
    def __init__(
        self,
        monitoring_config_repository: MonitoringConfigRepository,
        monitor_check_repository: MonitorCheckRepository,
    ):
        self._monitoring_config_repository = (
            monitoring_config_repository
        )
        self._monitor_check_repository = monitor_check_repository

    async def get_latest_for_owner(
        self,
        *,
        project_id: UUID,
        service_id: UUID,
        owner_id: UUID,
    ) -> MonitorCheck | None:
        config = (
            await self._monitoring_config_repository
            .get_by_service_for_owner(
                service_id=service_id,
                project_id=project_id,
                owner_id=owner_id,
            )
        )

        if config is None:
            return None

        return await self._monitor_check_repository.get_latest_for_config(
            config.id
        )
    async def get_history_for_owner(
        self,
        *,
        project_id: UUID,
        service_id: UUID,
        owner_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[MonitorCheck], int] | None:
        config = (
            await self._monitoring_config_repository
            .get_by_service_for_owner(
                service_id=service_id,
                project_id=project_id,
                owner_id=owner_id,
            )
        )

        if config is None:
            return None

        checks = await self._monitor_check_repository.list_for_config(
            config.id,
            limit=limit,
            offset=offset,
        )

        total = await self._monitor_check_repository.count_for_config(
            config.id
        )

        return checks, total