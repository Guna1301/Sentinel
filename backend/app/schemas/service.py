from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Service name cannot be null")
        return value

    def model_dump_updates(self) -> dict:
        return self.model_dump(exclude_unset=True)


class ServiceResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}