"""Add scheduling metadata and time-series result partition fields.

Revision ID: 20260901_monitoring_scheduler_time_series
Revises: 20260901_fix_alembic_version_length
Create Date: 2026-09-01 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260901_monitoring_scheduler_time_series"
down_revision = "20260901_fix_alembic_version_length"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monitor_endpoints",
        sa.Column(
            "next_check_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.add_column(
        "monitor_endpoints",
        sa.Column("last_check_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_monitor_endpoints_next_check_at"),
        "monitor_endpoints",
        ["next_check_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_monitor_endpoints_last_check_at"),
        "monitor_endpoints",
        ["last_check_at"],
        unique=False,
    )
    op.add_column(
        "monitor_results",
        sa.Column(
            "partition_bucket",
            sa.String(length=7),
            nullable=False,
            server_default="1970-01",
        ),
    )
    op.create_index(
        op.f("ix_monitor_results_partition_bucket"),
        "monitor_results",
        ["partition_bucket"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_monitor_results_partition_bucket"), table_name="monitor_results"
    )
    op.drop_column("monitor_results", "partition_bucket")
    op.drop_index(
        op.f("ix_monitor_endpoints_last_check_at"), table_name="monitor_endpoints"
    )
    op.drop_index(
        op.f("ix_monitor_endpoints_next_check_at"), table_name="monitor_endpoints"
    )
    op.drop_column("monitor_endpoints", "last_check_at")
    op.drop_column("monitor_endpoints", "next_check_at")
