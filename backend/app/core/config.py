import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.environ["DATABASE_URL"]
    REDIS_URL: str = os.environ["REDIS_URL"]

    GOOGLE_CLIENT_ID: str = os.environ["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET: str = os.environ["GOOGLE_CLIENT_SECRET"]
    GOOGLE_REDIRECT_URI: str = os.environ["GOOGLE_REDIRECT_URI"]

    AUTH_COOKIE_NAME: str = "sentinel_session"
    AUTH_COOKIE_MAX_AGE: int = 60 * 60 * 24 * 7
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: str = "lax"

    FRONTEND_ORIGIN: str = os.environ["FRONTEND_ORIGIN"]


settings = Settings()