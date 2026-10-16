from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MonitorCheckResponse(BaseModel):
    id: UUID
    monitoring_config_id: UUID
    checked_at: datetime
    success: bool
    status_code: int | None
    latency_ms: int | None
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

class MonitorCheckHistoryResponse(BaseModel):
    items: list[MonitorCheckResponse]
    total: int
    limit: int
    offset: int