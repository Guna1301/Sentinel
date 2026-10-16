from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.repositories.monitor_check import MonitorCheckRepository
from app.repositories.monitoring_config import (
    MonitoringConfigRepository,
)

from app.services.monitor_check import MonitorCheckService

from app.schemas.monitor_check import (
    MonitorCheckHistoryResponse,
    MonitorCheckResponse,
)

router = APIRouter(
    prefix=(
        "/api/projects/{project_id}/services/{service_id}"
        "/monitoring/checks"
    ),
    tags=["monitoring"],
)


def get_monitor_check_service(
    session: AsyncSession,
) -> MonitorCheckService:
    return MonitorCheckService(
        monitoring_config_repository=MonitoringConfigRepository(
            session
        ),
        monitor_check_repository=MonitorCheckRepository(session),
    )


@router.get(
    "/latest",
    response_model=MonitorCheckResponse,
)
async def get_latest_monitor_check(
    project_id: UUID,
    service_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_monitor_check_service(session)

    check = await service.get_latest_for_owner(
        project_id=project_id,
        service_id=service_id,
        owner_id=current_user.id,
    )

    if check is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring check not found",
        )

    return check

@router.get(
    "",
    response_model=MonitorCheckHistoryResponse,
)
async def list_monitor_checks(
    project_id: UUID,
    service_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_monitor_check_service(session)

    result = await service.get_history_for_owner(
        project_id=project_id,
        service_id=service_id,
        owner_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring configuration not found",
        )

    checks, total = result

    return MonitorCheckHistoryResponse(
        items=checks,
        total=total,
        limit=limit,
        offset=offset,
    )