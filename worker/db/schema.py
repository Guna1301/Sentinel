from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table
from sqlalchemy.dialects.postgresql import UUID


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