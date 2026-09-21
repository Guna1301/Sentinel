import pytest

from app.clients.google import GoogleOAuthClient
from app.core.config import settings


class FakeGoogleResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class FakeHttpClient:
    def __init__(self):
        self.calls = []

    async def post(self, url, data):
        self.calls.append({
            "url": url,
            "data": data,
        })

        return FakeGoogleResponse(
            {
                "access_token": "test-access-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "id_token": "test-id-token",
            }
        )


@pytest.mark.asyncio
async def test_exchange_code_sends_expected_request():
    client = FakeHttpClient()
    google = GoogleOAuthClient(client)

    result = await google.exchange_code("authorization-code")

    assert result.access_token == "test-access-token"
    assert result.token_type == "Bearer"
    assert result.expires_in == 3600
    assert result.id_token == "test-id-token"

    assert len(client.calls) == 1

    request = client.calls[0]

    assert request["url"] == "https://oauth2.googleapis.com/token"

    assert request["data"]["code"] == "authorization-code"
    assert request["data"]["client_id"] == settings.GOOGLE_CLIENT_ID
    assert request["data"]["client_secret"] == settings.GOOGLE_CLIENT_SECRET
    assert request["data"]["redirect_uri"] == settings.GOOGLE_REDIRECT_URI
    assert request["data"]["grant_type"] == "authorization_code"