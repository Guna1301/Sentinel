
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID


IncidentAction = Literal["none", "open", "resolve"]


@dataclass(frozen=True, slots=True)
class IncidentDecision:
    action: IncidentAction
    reason: str
    incident_id: UUID | None = None
    trigger_check_id: UUID | None = None
    occurred_at: datetime | None = None


FAILURE_THRESHOLD = 3


def determine_incident_transition(
    checks: Sequence[Mapping[str, Any]],
    open_incident: Mapping[str, Any] | None,
    *,
    failure_threshold: int = FAILURE_THRESHOLD,
) -> IncidentDecision:
    """
    Determine the transition from checks ordered newest first.

    This function has no database or network dependencies.
    """
    if failure_threshold < 1:
        raise ValueError("failure_threshold must be positive")

    if not checks:
        return IncidentDecision(
            action="none",
            reason="no_checks",
        )

    latest = checks[0]

    if latest["success"]:
        if open_incident is None:
            return IncidentDecision(
                action="none",
                reason="latest_check_success",
            )

        return IncidentDecision(
            action="resolve",
            reason="successful_check",
            incident_id=open_incident["id"],
            occurred_at=latest["checked_at"],
        )

    if open_incident is not None:
        return IncidentDecision(
            action="none",
            reason="incident_already_open",
            incident_id=open_incident["id"],
        )

    consecutive_failures = 0

    for check in checks[:failure_threshold]:
        if check["success"]:
            break

        consecutive_failures += 1

    if consecutive_failures < failure_threshold:
        return IncidentDecision(
            action="none",
            reason="failure_threshold_not_reached",
        )

    return IncidentDecision(
        action="open",
        reason="failure_threshold_reached",
        trigger_check_id=latest["id"],
        occurred_at=latest["checked_at"],
    )
