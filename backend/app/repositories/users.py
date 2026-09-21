from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.google import GoogleIdentity


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_google_subject(
        self,
        google_subject: str,
    ) -> User | None:
        result = await self._session.execute(
            select(User).where(
                User.google_subject == google_subject
            )
        )

        return result.scalar_one_or_none()

    async def create_from_google_identity(
        self,
        identity: GoogleIdentity,
    ) -> User:
        user = User(
            google_subject=identity.subject,
            email=identity.email,
            name=identity.name,
            avatar_url=identity.avatar_url,
        )

        self._session.add(user)
        await self._session.flush()

        return user