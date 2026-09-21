from uuid import UUID

from pydantic import BaseModel, Field


class GoogleCodeRequest(BaseModel):
    code: str = Field(min_length=1)


class AuthUserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    avatar_url: str | None = None


class GoogleAuthResponse(BaseModel):
    user: AuthUserResponse