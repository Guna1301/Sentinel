import httpx
import pytest
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.session import Session

from app.api.dependencies import get_db_session
from app.core.database import AsyncSessionLocal
from app.main import app

from unittest.mock import AsyncMock, patch

from app.schemas.google import GoogleIdentity, GoogleTokenResponse


from contextlib import asynccontextmanager


@asynccontextmanager
async def app_lifespan():
    async with app.router.lifespan_context(app):
        yield

@pytest.fixture
def override_db_session():
    async def _override_db_session():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_db_session

    yield

    app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_auth_routes_are_registered():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/auth/google/code" in paths
    assert "/api/auth/me" in paths
    assert "/api/auth/logout" in paths


@pytest.mark.asyncio
async def test_google_auth_rejects_invalid_origin():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/auth/google/code",
            json={"code": "test-code"},
            headers={
                "Origin": "http://malicious.example",
                "X-Requested-With": "XmlHttpRequest",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid request origin"


@pytest.mark.asyncio
async def test_google_auth_rejects_missing_requested_with_header():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/auth/google/code",
            json={"code": "test-code"},
            headers={
                "Origin": "http://localhost:5173",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid authentication request"


@pytest.mark.asyncio
async def test_google_auth_rejects_invalid_requested_with_header():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/auth/google/code",
            json={"code": "test-code"},
            headers={
                "Origin": "http://localhost:5173",
                "X-Requested-With": "wrong-value",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid authentication request"

@pytest.mark.asyncio
async def test_google_auth_creates_user_session_and_cookie(override_db_session):
    fake_identity = GoogleIdentity(
        subject="google-subject-123",
        email="test@example.com",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
    )

    fake_token_response = GoogleTokenResponse(
        access_token="fake-access-token",
        token_type="Bearer",
        expires_in=3600,
        id_token="fake-id-token",
    )

    transport = httpx.ASGITransport(app=app)

    with (
        patch(
            "app.api.auth.GoogleOAuthClient.exchange_code",
            new_callable=AsyncMock,
            return_value=fake_token_response,
        ),
        patch(
            "app.api.auth.GoogleIdentityValidator.verify",
            return_value=fake_identity,
        ),
    ):
        async with app_lifespan():
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    "/api/auth/google/code",
                    json={"code": "fake-google-code"},
                    headers={
                        "Origin": "http://localhost:5173",
                        "X-Requested-With": "XmlHttpRequest",
                    },
                )

    assert response.status_code == 200

    body = response.json()

    assert body["user"]["email"] == "test@example.com"
    assert body["user"]["name"] == "Test User"
    assert body["user"]["avatar_url"] == "https://example.com/avatar.jpg"
    assert "id" in body["user"]

    set_cookie = response.headers["set-cookie"]

    assert "sentinel_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie

@pytest.mark.asyncio
async def test_authenticated_user_can_access_me(override_db_session):
    fake_identity = GoogleIdentity(
        subject="google-subject-me-123",
        email="me@example.com",
        name="Me User",
        avatar_url="https://example.com/me.jpg",
    )

    fake_token_response = GoogleTokenResponse(
        access_token="fake-access-token",
        token_type="Bearer",
        expires_in=3600,
        id_token="fake-id-token",
    )

    transport = httpx.ASGITransport(app=app)

    with (
        patch(
            "app.api.auth.GoogleOAuthClient.exchange_code",
            new_callable=AsyncMock,
            return_value=fake_token_response,
        ),
        patch(
            "app.api.auth.GoogleIdentityValidator.verify",
            return_value=fake_identity,
        ),
    ):
        async with app_lifespan():
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                login_response = await client.post(
                    "/api/auth/google/code",
                    json={"code": "fake-google-code"},
                    headers={
                        "Origin": "http://localhost:5173",
                        "X-Requested-With": "XmlHttpRequest",
                    },
                )

                assert login_response.status_code == 200

                me_response = await client.get("/api/auth/me")

    assert me_response.status_code == 200

    body = me_response.json()

    assert body["email"] == "me@example.com"
    assert body["name"] == "Me User"
    assert body["avatar_url"] == "https://example.com/me.jpg"
    assert "id" in body

@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookie(override_db_session):
    fake_identity = GoogleIdentity(
        subject="google-subject-logout-123",
        email="logout@example.com",
        name="Logout User",
    )

    fake_token_response = GoogleTokenResponse(
        access_token="fake-access-token",
        token_type="Bearer",
        expires_in=3600,
        id_token="fake-id-token",
    )

    transport = httpx.ASGITransport(app=app)

    with (
        patch(
            "app.api.auth.GoogleOAuthClient.exchange_code",
            new_callable=AsyncMock,
            return_value=fake_token_response,
        ),
        patch(
            "app.api.auth.GoogleIdentityValidator.verify",
            return_value=fake_identity,
        ),
    ):
        async with app_lifespan():
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                login_response = await client.post(
                    "/api/auth/google/code",
                    json={"code": "fake-google-code"},
                    headers={
                        "Origin": "http://localhost:5173",
                        "X-Requested-With": "XmlHttpRequest",
                    },
                )

                assert login_response.status_code == 200

                session_cookie = client.cookies.get("sentinel_session")
                assert session_cookie is not None

                me_response = await client.get("/api/auth/me")
                assert me_response.status_code == 200

                logout_response = await client.post("/api/auth/logout")

                assert logout_response.status_code == 204

                set_cookie = logout_response.headers["set-cookie"]

                assert "sentinel_session=" in set_cookie
                assert "Max-Age=0" in set_cookie
                assert "Path=/" in set_cookie

                me_after_logout = await client.get("/api/auth/me")

    assert me_after_logout.status_code == 401
    assert me_after_logout.json()["detail"] == "Authentication required"

    token_hash = hashlib.sha256(
        session_cookie.encode("utf-8")
    ).hexdigest()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Session).where(Session.token_hash == token_hash)
        )
        stored_session = result.scalar_one()

        assert stored_session.revoked_at is not None

@pytest.mark.asyncio
async def test_google_auth_failure_returns_401(override_db_session):
    transport = httpx.ASGITransport(app=app)

    with patch(
        "app.api.auth.GoogleOAuthClient.exchange_code",
        new_callable=AsyncMock,
        side_effect=httpx.HTTPStatusError(
            "Google rejected authorization code",
            request=httpx.Request(
                "POST",
                "https://oauth2.googleapis.com/token",
            ),
            response=httpx.Response(400),
        ),
    ):
        async with app_lifespan():
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    "/api/auth/google/code",
                    json={"code": "invalid-google-code"},
                    headers={
                        "Origin": "http://localhost:5173",
                        "X-Requested-With": "XmlHttpRequest",
                    },
                )

    assert response.status_code == 401
    assert response.json()["detail"] == "Google authentication failed"