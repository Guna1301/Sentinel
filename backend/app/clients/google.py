import httpx

from app.core.config import settings
from app.schemas.google import GoogleTokenResponse


class GoogleOAuthClient:
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def exchange_code(self, code: str) -> GoogleTokenResponse:
        response = await self._client.post(
            self.TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        response.raise_for_status()

        return GoogleTokenResponse.model_validate(response.json())