from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.repositories.monitoring_config import MonitoringConfigRepository
from app.schemas.monitoring_config import (
    MonitoringConfigCreate,
    MonitoringConfigResponse,
    MonitoringConfigUpdate,
    MonitoringCheckEnqueueResponse,
)
from app.services.monitoring_config import MonitoringConfigService

from redis.exceptions import RedisError

router = APIRouter(
    prefix="/api/projects/{project_id}/services/{service_id}/monitoring",
    tags=["monitoring"],
)


def get_monitoring_config_service(
    session: AsyncSession,
) -> MonitoringConfigService:
    repository = MonitoringConfigRepository(session)
    return MonitoringConfigService(repository)


@router.post(
    "",
    response_model=MonitoringConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_monitoring_config(
    project_id: UUID,
    service_id: UUID,
    payload: MonitoringConfigCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_monitoring_config_service(session)

    existing = await service.get_config(
        service_id=service_id,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Monitoring configuration already exists",
        )

    created = await service.create_config(
        service_id=service_id,
        project_id=project_id,
        owner_id=current_user.id,
        url=str(payload.url),
        method=payload.method,
        interval_seconds=payload.interval_seconds,
        timeout_seconds=payload.timeout_seconds,
        enabled=payload.enabled,
    )

    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    await session.commit()
    await session.refresh(created)

    return created


@router.get(
    "",
    response_model=MonitoringConfigResponse,
)
async def get_monitoring_config(
    project_id: UUID,
    service_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_monitoring_config_service(session)

    config = await service.get_config(
        service_id=service_id,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring configuration not found",
        )

    return config


@router.post(
    "/run",
    response_model=MonitoringCheckEnqueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_monitoring_check(
    project_id: UUID,
    service_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_monitoring_config_service(session)

    config = await service.get_config(
        service_id=service_id,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring configuration not found",
        )

    try:
        job = await request.app.state.queue.enqueue(
            "check_monitor",
            str(config.id),
        )
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Monitoring queue is unavailable",
        ) from exc

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Monitoring check could not be queued",
        )

    return {
        "status": "queued",
        "job_id": job.job_id,
    }

@router.patch(
    "",
    response_model=MonitoringConfigResponse,
)
async def update_monitoring_config(
    project_id: UUID,
    service_id: UUID,
    payload: MonitoringConfigUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_monitoring_config_service(session)

    config = await service.get_config(
        service_id=service_id,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring configuration not found",
        )

    updates = payload.model_dump_updates()

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided",
        )

    updated = await service.update_config(
        config=config,
        **updates,
    )

    await session.commit()
    await session.refresh(updated)

    return updated


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_monitoring_config(
    project_id: UUID,
    service_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_monitoring_config_service(session)

    config = await service.get_config(
        service_id=service_id,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring configuration not found",
        )

    await service.delete_config(config)

    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)