
import uuid
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

    The caller must already have locked the corresponding
    monitoring_configs row with SELECT ... FOR UPDATE.

    This function participates in the caller's transaction.
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
            return IncidentDecision(
                action="none",
                reason="incident_already_resolved",
                incident_id=decision.incident_id,
            )

    return decision


async def evaluate_incident_for_config(
    monitoring_config_id: UUID,
) -> IncidentDecision:
    """
    Safely evaluate a persisted configuration's current check state.

    M8.2 provides this standalone evaluation operation.
    M8.3 will integrate it with check creation in one transaction.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            config_result = await session.execute(
                select(monitoring_configs.c.id)
                .where(
                    monitoring_configs.c.id == monitoring_config_id
                )
                .with_for_update()
            )

            if config_result.scalar_one_or_none() is None:
                return IncidentDecision(
                    action="none",
                    reason="configuration_not_found",
                )

            return await evaluate_incident_in_transaction(
                session,
                monitoring_config_id,
            )
