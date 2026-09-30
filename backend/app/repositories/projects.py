from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        owner_id: UUID,
        name: str,
        description: str | None,
    ) -> Project:
        project = Project(
            owner_id=owner_id,
            name=name,
            description=description,
        )

        self._session.add(project)
        await self._session.flush()

        return project

    async def list_by_owner(self, owner_id: UUID) -> list[Project]:
        result = await self._session.execute(
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc())
        )

        return list(result.scalars().all())

    async def get_by_id(
        self,
        project_id: UUID,
        owner_id: UUID,
    ) -> Project | None:
        result = await self._session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == owner_id,
            )
        )

        return result.scalar_one_or_none()

    async def delete(self, project: Project) -> None:
        await self._session.delete(project)
        await self._session.flush()