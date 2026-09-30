from uuid import UUID

from app.models.project import Project
from app.repositories.projects import ProjectRepository


class ProjectService:
    def __init__(self, repository: ProjectRepository):
        self._repository = repository

    async def create_project(
        self,
        owner_id: UUID,
        name: str,
        description: str | None,
    ) -> Project:
        return await self._repository.create(
            owner_id=owner_id,
            name=name,
            description=description,
        )

    async def list_projects(self, owner_id: UUID) -> list[Project]:
        return await self._repository.list_by_owner(owner_id)

    async def get_project(
        self,
        project_id: UUID,
        owner_id: UUID,
    ) -> Project | None:
        return await self._repository.get_by_id(
            project_id=project_id,
            owner_id=owner_id,
        )

    async def update_project(
        self,
        project: Project,
        **updates
    ) -> Project:
        if "name" in updates:
            project.name = updates["name"]
        if "description" in updates:
            project.description = updates["description"]

        return project

    async def delete_project(self, project: Project) -> None:
        await self._repository.delete(project)