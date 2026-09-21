import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


class SessionService:
    SESSION_LIFETIME = timedelta(days=7)

    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create_session(self, user_id: uuid.UUID) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)

        session = Session(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + self.SESSION_LIFETIME,
        )

        self._session.add(session)
        await self._session.flush()

        return token

    async def get_user_id(self, token: str) -> uuid.UUID | None:
        token_hash = self._hash_token(token)

        result = await self._session.execute(
            select(Session.user_id).where(
                Session.token_hash == token_hash,
                Session.revoked_at.is_(None),
                Session.expires_at > datetime.now(timezone.utc),
            )
        )

        return result.scalar_one_or_none()

    async def revoke_session(self, token: str) -> None:
        token_hash = self._hash_token(token)

        result = await self._session.execute(
            select(Session).where(
                Session.token_hash == token_hash,
                Session.revoked_at.is_(None),
            )
        )

        session = result.scalar_one_or_none()

        if session is not None:
            session.revoked_at = datetime.now(timezone.utc)
            await self._session.flush()