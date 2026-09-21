from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.api.dependencies import get_db_session, get_current_user
from app.clients.google import GoogleOAuthClient
from app.clients.google_identity import GoogleIdentityValidator
from app.core.config import settings
from app.schemas.auth import (
    AuthUserResponse,
    GoogleAuthResponse,
    GoogleCodeRequest,
)
from app.services.auth import AuthService

from app.models.user import User
from app.services.session import SessionService


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/google/code",
    response_model=GoogleAuthResponse,
)
async def authenticate_with_google(
    payload: GoogleCodeRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
):
    origin = request.headers.get("origin")
    requested_with = request.headers.get("x-requested-with")

    if origin != settings.FRONTEND_ORIGIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid request origin",
        )

    if requested_with != "XmlHttpRequest":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication request",
        )

    google_client = GoogleOAuthClient(
        request.app.state.http_client
    )

    google_identity_validator = GoogleIdentityValidator()

    auth_service = AuthService(
        session=session,
        google_client=google_client,
        google_identity_validator=google_identity_validator,
    )

    try:
        user, session_token = await auth_service.authenticate_with_google(
            payload.code
        )
    except (ValueError, httpx.HTTPError) as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed",
        ) from exc
    except Exception:
        await session.rollback()
        raise

    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=session_token,
        max_age=settings.AUTH_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/",
    )

    return GoogleAuthResponse(
        user=AuthUserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
        )
    )


@router.get(
    "/me",
    response_model=AuthUserResponse,
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> AuthUserResponse:
    return AuthUserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
    )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
):
    session_token = request.cookies.get(settings.AUTH_COOKIE_NAME)

    if session_token:
        session_service = SessionService(session)
        await session_service.revoke_session(session_token)
        await session.commit()

    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
    )