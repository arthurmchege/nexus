"""Add monitor health state and incidents.

Revision ID: 20260909_alert_incidents
Revises: 20260902_monitoring_result_indexes
"""

import sqlalchemy as sa

from alembic import op

revision = "20260909_alert_incidents"
down_revision = "20260902_monitoring_result_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monitor_endpoints",
        sa.Column("health_state", sa.String(length=16), nullable=False, server_default="up"),
    )
    op.add_column(
        "monitor_endpoints",
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "monitor_endpoints",
        sa.Column("consecutive_successes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "monitor_endpoints",
        sa.Column("failure_threshold", sa.Integer(), nullable=False, server_default="2"),
    )
    op.add_column(
        "monitor_endpoints",
        sa.Column("recovery_threshold", sa.Integer(), nullable=False, server_default="2"),
    )
    op.create_index(
        "ix_monitor_endpoints_health_state",
        "monitor_endpoints",
        ["health_state"],
        unique=False,
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("monitor_id", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("trigger_reason", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.ForeignKeyConstraint(["monitor_id"], ["monitor_endpoints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidents_id", "incidents", ["id"], unique=False)
    op.create_index("ix_incidents_monitor_id", "incidents", ["monitor_id"], unique=False)
    op.create_index("ix_incidents_status", "incidents", ["status"], unique=False)
    op.create_index(
        "uq_incidents_open_monitor",
        "incidents",
        ["monitor_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
        sqlite_where=sa.text("status = 'open'"),
    )
    op.create_index(
        "ix_incidents_status_opened_at",
        "incidents",
        ["status", "opened_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_incidents_status_opened_at", table_name="incidents")
    op.drop_index("uq_incidents_open_monitor", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_monitor_id", table_name="incidents")
    op.drop_index("ix_incidents_id", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_monitor_endpoints_health_state", table_name="monitor_endpoints")
    op.drop_column("monitor_endpoints", "recovery_threshold")
    op.drop_column("monitor_endpoints", "failure_threshold")
    op.drop_column("monitor_endpoints", "consecutive_successes")
    op.drop_column("monitor_endpoints", "consecutive_failures")
    op.drop_column("monitor_endpoints", "health_state")
