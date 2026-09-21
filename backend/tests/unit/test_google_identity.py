import pytest

from app.clients.google_identity import GoogleIdentityValidator


def test_valid_google_identity_is_converted(monkeypatch):
    expected_payload = {
        "sub": "google-user-123",
        "email": "user@example.com",
        "name": "Test User",
        "picture": "https://example.com/avatar.jpg",
    }

    def fake_verify(token, request, audience):
        assert token == "test-id-token"
        return expected_payload

    monkeypatch.setattr(
        "app.clients.google_identity.id_token.verify_oauth2_token",
        fake_verify,
    )

    validator = GoogleIdentityValidator()

    identity = validator.verify("test-id-token")

    assert identity.subject == "google-user-123"
    assert identity.email == "user@example.com"
    assert identity.name == "Test User"
    assert identity.avatar_url == "https://example.com/avatar.jpg"


def test_invalid_google_token_is_rejected(monkeypatch):
    def fake_verify(token, request, audience):
        raise ValueError("invalid token")

    monkeypatch.setattr(
        "app.clients.google_identity.id_token.verify_oauth2_token",
        fake_verify,
    )

    validator = GoogleIdentityValidator()

    with pytest.raises(ValueError, match="Invalid Google identity token"):
        validator.verify("tampered-token")


def test_missing_subject_is_rejected(monkeypatch):
    def fake_verify(token, request, audience):
        return {
            "email": "user@example.com",
            "name": "Test User",
        }

    monkeypatch.setattr(
        "app.clients.google_identity.id_token.verify_oauth2_token",
        fake_verify,
    )

    validator = GoogleIdentityValidator()

    with pytest.raises(
        ValueError,
        match="Google identity is missing required claims",
    ):
        validator.verify("test-id-token")