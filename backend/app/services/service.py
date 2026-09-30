from uuid import UUID

from app.models.service import Service
from app.repositories.service import ServiceRepository


class ServiceService:
    def __init__(self, repository: ServiceRepository):
        self._repository = repository

    async def create_service(
        self,
        project_id: UUID,
        owner_id: UUID,
        name: str,
        description: str | None,
    ) -> Service | None:
        project_exists = await self._repository.project_belongs_to_owner(
            project_id=project_id,
            owner_id=owner_id,
        )

        if not project_exists:
            return None

        return await self._repository.create(
            project_id=project_id,
            name=name,
            description=description,
        )

    async def list_services(
        self,
        project_id: UUID,
        owner_id: UUID,
    ) -> list[Service]:
        return await self._repository.list_by_project_for_owner(
            project_id=project_id,
            owner_id=owner_id,
        )

    async def get_service(
        self,
        service_id: UUID,
        project_id: UUID,
        owner_id: UUID,
    ) -> Service | None:
        return await self._repository.get_by_id_for_owner(
            service_id=service_id,
            project_id=project_id,
            owner_id=owner_id,
        )

    async def update_service(
        self,
        service: Service,
        **updates,
    ) -> Service:
        if "name" in updates and updates["name"] is not None:
            service.name = updates["name"]

        if "description" in updates:
            service.description = updates["description"]

        return service

    async def delete_service(
        self,
        service: Service,
    ) -> None:
        await self._repository.delete(service)