from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.service import Service


class ServiceRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def project_belongs_to_owner(
        self,
        project_id: UUID,
        owner_id: UUID,
    ) -> bool:
        result = await self._session.execute(
            select(Project.id).where(
                Project.id == project_id,
                Project.owner_id == owner_id,
            )
        )

        return result.scalar_one_or_none() is not None

    async def create(
        self,
        project_id: UUID,
        name: str,
        description: str | None,
    ) -> Service:
        service = Service(
            project_id=project_id,
            name=name,
            description=description,
        )

        self._session.add(service)
        await self._session.flush()

        return service

    async def list_by_project_for_owner(
        self,
        project_id: UUID,
        owner_id: UUID,
    ) -> list[Service]:
        result = await self._session.execute(
            select(Service)
            .join(Project, Project.id == Service.project_id)
            .where(
                Service.project_id == project_id,
                Project.owner_id == owner_id,
            )
            .order_by(Service.created_at.desc())
        )

        return list(result.scalars().all())

    async def get_by_id_for_owner(
        self,
        service_id: UUID,
        project_id: UUID,
        owner_id: UUID,
    ) -> Service | None:
        result = await self._session.execute(
            select(Service)
            .join(Project, Project.id == Service.project_id)
            .where(
                Service.id == service_id,
                Service.project_id == project_id,
                Project.owner_id == owner_id,
            )
        )

        return result.scalar_one_or_none()

    async def delete(
        self,
        service: Service,
    ) -> None:
        await self._session.delete(service)
        await self._session.flush()