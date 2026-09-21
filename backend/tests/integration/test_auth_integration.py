import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.session import Session
from app.models.user import User
from app.services.session import SessionService


@pytest.mark.asyncio
async def test_session_creation_stores_only_hashed_token():
    async with AsyncSessionLocal() as db:
        user = User(
            google_subject=f"test-google-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            name="Test User",
        )

        db.add(user)
        await db.flush()

        service = SessionService(db)

        raw_token = await service.create_session(user.id)

        assert raw_token
        assert len(raw_token) > 0

        result = await db.execute(
            select(Session).where(Session.user_id == user.id)
        )
        stored_session = result.scalar_one()

        expected_hash = hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

        assert stored_session.token_hash == expected_hash
        assert stored_session.token_hash != raw_token
        assert stored_session.revoked_at is None
        assert stored_session.expires_at > datetime.now(timezone.utc)

        await db.rollback()

@pytest.mark.asyncio
async def test_valid_session_resolves_user():
    async with AsyncSessionLocal() as db:
        user = User(
            google_subject=f"test-google-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            name="Test User",
        )
        db.add(user)
        await db.flush()

        service = SessionService(db)
        raw_token = await service.create_session(user.id)

        resolved_user_id = await service.get_user_id(raw_token)

        assert resolved_user_id == user.id

        await db.rollback()


@pytest.mark.asyncio
async def test_invalid_session_token_returns_none():
    async with AsyncSessionLocal() as db:
        service = SessionService(db)

        result = await service.get_user_id("invalid-session-token")

        assert result is None

        await db.rollback()


@pytest.mark.asyncio
async def test_expired_session_returns_none():
    async with AsyncSessionLocal() as db:
        user = User(
            google_subject=f"test-google-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            name="Test User",
        )
        db.add(user)
        await db.flush()

        service = SessionService(db)
        raw_token = await service.create_session(user.id)

        result = await db.execute(
            select(Session).where(Session.user_id == user.id)
        )
        stored_session = result.scalar_one()

        stored_session.expires_at = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        )
        await db.flush()

        resolved_user_id = await service.get_user_id(raw_token)

        assert resolved_user_id is None

        await db.rollback()


@pytest.mark.asyncio
async def test_revoked_session_returns_none():
    async with AsyncSessionLocal() as db:
        user = User(
            google_subject=f"test-google-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            name="Test User",
        )
        db.add(user)
        await db.flush()

        service = SessionService(db)
        raw_token = await service.create_session(user.id)

        await service.revoke_session(raw_token)

        resolved_user_id = await service.get_user_id(raw_token)

        assert resolved_user_id is None

        await db.rollback()