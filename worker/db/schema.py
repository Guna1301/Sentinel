from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import CheckConstraint, ForeignKey, Index, text

metadata = MetaData()


monitoring_configs = Table(
    "monitoring_configs",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
    ),
    Column(
        "url",
        String(2048),
        nullable=False,
    ),
    Column(
        "method",
        String(10),
        nullable=False,
    ),
    Column(
        "timeout_seconds",
        Integer,
        nullable=False,
    ),
    Column(
        "enabled",
        Boolean,
        nullable=False,
    ),
    Column(
        "interval_seconds",
        Integer,
        nullable=False,
    ),
    Column(
        "next_check_at",
        DateTime(timezone=True),
        nullable=False,
    ),
)


monitor_checks = Table(
    "monitor_checks",
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
    ),
    Column(
        "monitoring_config_id",
        UUID(as_uuid=True),
        nullable=False,
    ),
    Column(
        "checked_at",
        DateTime(timezone=True),
        nullable=False,
    ),
    Column(
        "success",
        Boolean,
        nullable=False,
    ),
    Column(
        "status_code",
        Integer,
        nullable=True,
    ),
    Column(
        "latency_ms",
        Integer,
        nullable=True,
    ),
    Column(
        "error",
        String(2048),
        nullable=True,
    ),
)

incidents = Table(
    "incidents",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "monitoring_config_id",
        UUID(as_uuid=True),
        ForeignKey("monitoring_configs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "trigger_check_id",
        UUID(as_uuid=True),
        ForeignKey("monitor_checks.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("status", String(20), nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
    CheckConstraint(
        "status IN ('open', 'resolved')",
        name="ck_incidents_status",
    ),
    CheckConstraint(
        """
        (status = 'open' AND resolved_at IS NULL)
        OR
        (status = 'resolved' AND resolved_at IS NOT NULL)
        """,
        name="ck_incidents_resolution_state",
    ),
)

Index(
    "uq_incidents_one_open_per_config",
    incidents.c.monitoring_config_id,
    unique=True,
    postgresql_where=text("status = 'open'"),
)

Index(
    "ix_incidents_config_opened",
    incidents.c.monitoring_config_id,
    incidents.c.opened_at,
)