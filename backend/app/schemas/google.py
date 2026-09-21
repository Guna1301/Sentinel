from pydantic import BaseModel


class GoogleTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    id_token: str


class GoogleIdentity(BaseModel):
    subject: str
    email: str
    name: str
    avatar_url: str | None = None