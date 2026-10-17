
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    __table_args__ = (
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
        Index(
            "uq_incidents_one_open_per_config",
            "monitoring_config_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        Index(
            "ix_incidents_config_opened",
            "monitoring_config_id",
            "opened_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    monitoring_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monitoring_configs.id", ondelete="CASCADE"),
        nullable=False,
    )

    trigger_check_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monitor_checks.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default="open",
    )

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    monitoring_config = relationship(
        "MonitoringConfig",
        back_populates="incidents",
    )
