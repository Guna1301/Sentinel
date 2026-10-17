
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import AsyncSessionLocal
from db.schema import incidents, monitor_checks, monitoring_configs
from services.incidents import (
    FAILURE_THRESHOLD,
    IncidentDecision,
    determine_incident_transition,
)


async def evaluate_incident_in_transaction(
    session: AsyncSession,
    monitoring_config_id: UUID,
) -> IncidentDecision:
    """
    Evaluate recent checks and apply an incident transition.

    The caller must hold a FOR UPDATE lock on the associated
    monitoring_configs row until the transaction completes.
    """
    open_result = await session.execute(
        select(
            incidents.c.id,
            incidents.c.opened_at,
        )
        .where(
            incidents.c.monitoring_config_id == monitoring_config_id,
            incidents.c.status == "open",
        )
        .with_for_update()
    )
    open_incident = open_result.mappings().one_or_none()

    check_result = await session.execute(
        select(
            monitor_checks.c.id,
            monitor_checks.c.checked_at,
            monitor_checks.c.success,
        )
        .where(
            monitor_checks.c.monitoring_config_id
            == monitoring_config_id
        )
        .order_by(
            monitor_checks.c.checked_at.desc(),
            monitor_checks.c.id.desc(),
        )
        .limit(FAILURE_THRESHOLD)
    )
    checks = list(check_result.mappings().all())

    decision = determine_incident_transition(
        checks,
        open_incident,
    )

    if decision.action == "open":
        if (
            decision.trigger_check_id is None
            or decision.occurred_at is None
        ):
            raise RuntimeError(
                "Incident-opening decision is missing required data"
            )

        incident_id = uuid.uuid4()

        await session.execute(
            insert(incidents).values(
                id=incident_id,
                monitoring_config_id=monitoring_config_id,
                trigger_check_id=decision.trigger_check_id,
                status="open",
                opened_at=decision.occurred_at,
                resolved_at=None,
            )
        )

        return IncidentDecision(
            action="open",
            reason=decision.reason,
            incident_id=incident_id,
            trigger_check_id=decision.trigger_check_id,
            occurred_at=decision.occurred_at,
        )

    if decision.action == "resolve":
        if (
            decision.incident_id is None
            or decision.occurred_at is None
        ):
            raise RuntimeError(
                "Incident-resolution decision is missing required data"
            )

        result = await session.execute(
            update(incidents)
            .where(
                incidents.c.id == decision.incident_id,
                incidents.c.monitoring_config_id
                == monitoring_config_id,
                incidents.c.status == "open",
            )
            .values(
                status="resolved",
                resolved_at=decision.occurred_at,
            )
        )

        if result.rowcount != 1:
            raise RuntimeError(
                "Open incident changed during a locked transition"
            )

    return decision


async def persist_check_and_evaluate_incident(
    *,
    monitoring_config_id: UUID,
    success: bool,
    status_code: int | None,
    latency_ms: int,
    error: str | None,
) -> tuple[UUID, IncidentDecision] | None:
    """
    Persist one check and apply its incident transition atomically.

    Returns None if the monitoring configuration no longer exists.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            config_result = await session.execute(
                select(monitoring_configs.c.id)
                .where(
                    monitoring_configs.c.id == monitoring_config_id,
                )
                .with_for_update()
            )

            if config_result.scalar_one_or_none() is None:
                return None

            check_id = uuid.uuid4()

            # Assign the timestamp after obtaining the configuration
            # lock, so incident evaluation follows serialized results.
            checked_at = datetime.now(timezone.utc)

            await session.execute(
                insert(monitor_checks).values(
                    id=check_id,
                    monitoring_config_id=monitoring_config_id,
                    checked_at=checked_at,
                    success=success,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    error=error,
                )
            )

            # Ensure this transaction can see the new check.
            await session.flush()

            decision = await evaluate_incident_in_transaction(
                session,
                monitoring_config_id,
            )

            return check_id, decision
