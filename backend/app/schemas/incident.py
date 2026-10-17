from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class IncidentResponse(BaseModel):
    id: UUID
    monitoring_config_id: UUID
    trigger_check_id: UUID | None
    status: Literal["open", "resolved"]
    opened_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class IncidentHistoryResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    limit: int
    offset: int