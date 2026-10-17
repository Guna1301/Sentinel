from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.repositories.incident import IncidentRepository
from app.repositories.monitoring_config import (
    MonitoringConfigRepository,
)
from app.schemas.incident import IncidentHistoryResponse
from app.services.incident import IncidentService


router = APIRouter(
    prefix=(
        "/api/projects/{project_id}/services/{service_id}"
        "/monitoring/incidents"
    ),
    tags=["incidents"],
)


def get_incident_service(
    session: AsyncSession,
) -> IncidentService:
    return IncidentService(
        monitoring_config_repository=MonitoringConfigRepository(
            session
        ),
        incident_repository=IncidentRepository(session),
    )


@router.get(
    "",
    response_model=IncidentHistoryResponse,
)
async def list_incidents(
    project_id: UUID,
    service_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    service = get_incident_service(session)

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

    items, total = result

    return IncidentHistoryResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )