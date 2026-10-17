from uuid import UUID

from app.models.incident import Incident
from app.repositories.incident import IncidentRepository
from app.repositories.monitoring_config import (
    MonitoringConfigRepository,
)


class IncidentService:
    def __init__(
        self,
        monitoring_config_repository: MonitoringConfigRepository,
        incident_repository: IncidentRepository,
    ):
        self._monitoring_config_repository = (
            monitoring_config_repository
        )
        self._incident_repository = incident_repository

    async def get_history_for_owner(
        self,
        *,
        project_id: UUID,
        service_id: UUID,
        owner_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[Incident], int] | None:
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

        items = await self._incident_repository.list_for_config(
            config.id,
            limit=limit,
            offset=offset,
        )

        total = await self._incident_repository.count_for_config(
            config.id
        )

        return items, total