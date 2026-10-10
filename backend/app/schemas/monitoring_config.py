from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

from typing import Literal

SUPPORTED_METHODS = {
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
}


class MonitoringConfigCreate(BaseModel):
    url: HttpUrl
    method: str = "GET"
    interval_seconds: int = Field(gt=0)
    timeout_seconds: int = Field(gt=0)
    enabled: bool = True

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        value = value.upper()

        if value not in SUPPORTED_METHODS:
            raise ValueError(
                f"Unsupported HTTP method: {value}"
            )

        return value


class MonitoringConfigUpdate(BaseModel):
    url: HttpUrl | None = None
    method: str | None = None
    interval_seconds: int | None = Field(default=None, gt=0)
    timeout_seconds: int | None = Field(default=None, gt=0)
    enabled: bool | None = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Method cannot be null")

        value = value.upper()

        if value not in SUPPORTED_METHODS:
            raise ValueError(
                f"Unsupported HTTP method: {value}"
            )

        return value

    def model_dump_updates(self) -> dict:
        return self.model_dump(exclude_unset=True)


class MonitoringConfigResponse(BaseModel):
    id: UUID
    service_id: UUID
    url: HttpUrl
    method: str
    interval_seconds: int
    timeout_seconds: int
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }

class MonitoringCheckEnqueueResponse(BaseModel):
    status: Literal["queued"] = "queued"
    job_id: str