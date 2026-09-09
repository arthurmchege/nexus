"""Add alert delivery records and monitor webhook configuration.

Revision ID: 20260909_alert_deliveries
Revises: 20260909_alert_incidents
"""

from alembic import op
import sqlalchemy as sa

revision = "20260909_alert_deliveries"
down_revision = "20260909_alert_incidents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monitor_endpoints",
        sa.Column("notification_webhook_url", sa.String(length=2048), nullable=True),
    )
    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=16), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "incident_id",
            "event",
            "channel",
            name="uq_alert_delivery_incident_event_channel",
        ),
    )
    op.create_index("ix_alert_deliveries_id", "alert_deliveries", ["id"], unique=False)
    op.create_index("ix_alert_deliveries_incident_id", "alert_deliveries", ["incident_id"], unique=False)
    op.create_index("ix_alert_deliveries_status", "alert_deliveries", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_alert_deliveries_status", table_name="alert_deliveries")
    op.drop_index("ix_alert_deliveries_incident_id", table_name="alert_deliveries")
    op.drop_index("ix_alert_deliveries_id", table_name="alert_deliveries")
    op.drop_table("alert_deliveries")
    op.drop_column("monitor_endpoints", "notification_webhook_url")
