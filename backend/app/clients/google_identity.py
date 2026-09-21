from google.auth import exceptions as google_auth_exceptions
from google.oauth2 import id_token
from google.auth.transport import requests

from app.core.config import settings
from app.schemas.google import GoogleIdentity


class GoogleIdentityValidator:
    def __init__(self):
        self._request = requests.Request()

    def verify(self, encoded_id_token: str) -> GoogleIdentity:
        try:
            payload = id_token.verify_oauth2_token(
                encoded_id_token,
                self._request,
                settings.GOOGLE_CLIENT_ID,
            )
        except (ValueError, google_auth_exceptions.GoogleAuthError) as exc:
            raise ValueError("Invalid Google identity token") from exc

        subject = payload.get("sub")
        email = payload.get("email")
        name = payload.get("name")

        if not subject or not email or not name:
            raise ValueError("Google identity is missing required claims")

        return GoogleIdentity(
            subject=subject,
            email=email,
            name=name,
            avatar_url=payload.get("picture"),
        )