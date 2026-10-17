
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from services.incidents import determine_incident_transition


CONFIG_INCIDENT_ID = UUID(
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
)


def make_check(
    check_id: str,
    *,
    minutes_ago: int,
    success: bool,
) -> dict:
    return {
        "id": UUID(check_id),
        "checked_at": (
            datetime.now(timezone.utc)
            - timedelta(minutes=minutes_ago)
        ),
        "success": success,
    }


def test_two_consecutive_failures_do_not_open_incident():
    checks = [
        make_check(
            "11111111-1111-4111-8111-111111111111",
            minutes_ago=0,
            success=False,
        ),
        make_check(
            "22222222-2222-4222-8222-222222222222",
            minutes_ago=1,
            success=False,
        ),
    ]

    decision = determine_incident_transition(checks, None)

    assert decision.action == "none"
    assert decision.reason == "failure_threshold_not_reached"


def test_three_consecutive_failures_open_incident():
    latest = make_check(
        "11111111-1111-4111-8111-111111111111",
        minutes_ago=0,
        success=False,
    )
    checks = [
        latest,
        make_check(
            "22222222-2222-4222-8222-222222222222",
            minutes_ago=1,
            success=False,
        ),
        make_check(
            "33333333-3333-4333-8333-333333333333",
            minutes_ago=2,
            success=False,
        ),
    ]

    decision = determine_incident_transition(checks, None)

    assert decision.action == "open"
    assert decision.reason == "failure_threshold_reached"
    assert decision.trigger_check_id == latest["id"]
    assert decision.occurred_at == latest["checked_at"]


def test_success_breaks_consecutive_failure_streak():
    checks = [
        make_check(
            "11111111-1111-4111-8111-111111111111",
            minutes_ago=0,
            success=True,
        ),
        make_check(
            "22222222-2222-4222-8222-222222222222",
            minutes_ago=1,
            success=False,
        ),
        make_check(
            "33333333-3333-4333-8333-333333333333",
            minutes_ago=2,
            success=False,
        ),
    ]

    decision = determine_incident_transition(checks, None)

    assert decision.action == "none"
    assert decision.reason == "latest_check_success"


def test_success_resolves_existing_incident():
    latest = make_check(
        "11111111-1111-4111-8111-111111111111",
        minutes_ago=0,
        success=True,
    )
    open_incident = {
        "id": CONFIG_INCIDENT_ID,
        "opened_at": latest["checked_at"] - timedelta(minutes=3),
    }

    decision = determine_incident_transition(
        [latest],
        open_incident,
    )

    assert decision.action == "resolve"
    assert decision.incident_id == CONFIG_INCIDENT_ID
    assert decision.occurred_at == latest["checked_at"]


def test_failure_does_not_create_duplicate_open_incident():
    latest = make_check(
        "11111111-1111-4111-8111-111111111111",
        minutes_ago=0,
        success=False,
    )
    open_incident = {
        "id": CONFIG_INCIDENT_ID,
        "opened_at": latest["checked_at"] - timedelta(minutes=3),
    }

    decision = determine_incident_transition(
        [latest],
        open_incident,
    )

    assert decision.action == "none"
    assert decision.reason == "incident_already_open"
    assert decision.incident_id == CONFIG_INCIDENT_ID
