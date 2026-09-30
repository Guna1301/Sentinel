from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.repositories.service import ServiceRepository
from app.schemas.service import (
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
)
from app.services.service import ServiceService


router = APIRouter(
    prefix="/api/projects/{project_id}/services",
    tags=["services"],
)


def get_service_service(session: AsyncSession) -> ServiceService:
    repository = ServiceRepository(session)
    return ServiceService(repository)


@router.post(
    "",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service(
    project_id: UUID,
    payload: ServiceCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_service_service(session)

    created = await service.create_service(
        project_id=project_id,
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )

    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await session.commit()
    await session.refresh(created)

    return created


@router.get(
    "",
    response_model=list[ServiceResponse],
)
async def list_services(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_service_service(session)

    return await service.list_services(
        project_id=project_id,
        owner_id=current_user.id,
    )


@router.get(
    "/{service_id}",
    response_model=ServiceResponse,
)
async def get_service(
    project_id: UUID,
    service_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_service_service(session)

    result = await service.get_service(
        service_id=service_id,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    return result


@router.patch(
    "/{service_id}",
    response_model=ServiceResponse,
)
async def update_service(
    project_id: UUID,
    service_id: UUID,
    payload: ServiceUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_service_service(session)

    existing = await service.get_service(
        service_id=service_id,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    updates = payload.model_dump_updates()

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided",
        )

    updated = await service.update_service(
        service=existing,
        **updates,
    )

    await session.commit()
    await session.refresh(updated)

    return updated


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_service(
    project_id: UUID,
    service_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_service_service(session)

    existing = await service.get_service(
        service_id=service_id,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    await service.delete_service(existing)

    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)