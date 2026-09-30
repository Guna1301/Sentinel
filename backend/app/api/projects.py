from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.repositories.projects import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_project_service(session: AsyncSession) -> ProjectService:
    return ProjectService(ProjectRepository(session))


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_project_service(session)

    project = await service.create_project(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )

    await session.commit()
    await session.refresh(project)

    return project


@router.get(
    "",
    response_model=list[ProjectResponse],
)
async def list_projects(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_project_service(session)

    return await service.list_projects(current_user.id)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_project_service(session)

    project = await service.get_project(
        project_id=project_id,
        owner_id=current_user.id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_project_service(session)

    project = await service.get_project(
        project_id=project_id,
        owner_id=current_user.id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    updates = payload.model_dump_updates()

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided",
        )

    project = await service.update_project(
        project=project,
        **updates,
    )

    await session.commit()
    await session.refresh(project)

    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_project_service(session)

    project = await service.get_project(
        project_id=project_id,
        owner_id=current_user.id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await service.delete_project(project)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)