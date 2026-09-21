from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.google import GoogleOAuthClient
from app.clients.google_identity import GoogleIdentityValidator
from app.models.user import User
from app.repositories.users import UserRepository
from app.services.session import SessionService


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        google_client: GoogleOAuthClient,
        google_identity_validator: GoogleIdentityValidator,
    ):
        self._session = session
        self._google_client = google_client
        self._google_identity_validator = google_identity_validator
        self._users = UserRepository(session)
        self._sessions = SessionService(session)

    async def authenticate_with_google(
        self,
        code: str,
    ) -> tuple[User, str]:
        token_response = await self._google_client.exchange_code(code)

        identity = self._google_identity_validator.verify(
            token_response.id_token
        )

        user = await self._users.get_by_google_subject(
            identity.subject
        )

        if user is None:
            user = await self._users.create_from_google_identity(
                identity
            )

        session_token = await self._sessions.create_session(
            user.id
        )

        await self._session.commit()

        return user, session_token