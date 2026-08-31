"""Add scheduler claim metadata for atomic monitor claiming.

Revision ID: 20260901_monitoring_scheduler_claim_locking
Revises: 20260901_monitoring_scheduler_time_series
Create Date: 2026-09-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260901_monitoring_scheduler_claim_locking"
down_revision = "20260901_monitoring_scheduler_time_series"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monitor_endpoints",
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "monitor_endpoints",
        sa.Column("claimed_by", sa.String(length=128), nullable=True),
    )
    op.create_index(
        op.f("ix_monitor_endpoints_claimed_at"),
        "monitor_endpoints",
        ["claimed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_monitor_endpoints_claimed_by"),
        "monitor_endpoints",
        ["claimed_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_monitor_endpoints_claimed_by"), table_name="monitor_endpoints")
    op.drop_index(op.f("ix_monitor_endpoints_claimed_at"), table_name="monitor_endpoints")
    op.drop_column("monitor_endpoints", "claimed_by")
    op.drop_column("monitor_endpoints", "claimed_at")
