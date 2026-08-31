"""Add monitoring domain tables

Revision ID: 20240831_monitoring_models
Revises: 20240831_init
Create Date: 2026-08-31 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20240831_monitoring_models"
down_revision = "20240831_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monitor_endpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("http_method", sa.String(length=10), nullable=False),
        sa.Column("expected_status_code", sa.Integer(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url", "http_method", name="uq_monitor_endpoint_url_method"),
        sa.CheckConstraint("interval_seconds >= 10", name="ck_monitor_interval_min"),
        sa.CheckConstraint("timeout_seconds >= 1", name="ck_monitor_timeout_min"),
        sa.CheckConstraint("expected_status_code >= 100", name="ck_monitor_expected_status_min"),
        sa.CheckConstraint("expected_status_code <= 599", name="ck_monitor_expected_status_max"),
    )
    op.create_index(op.f("ix_monitor_endpoints_active"), "monitor_endpoints", ["active"], unique=False)
    op.create_index(op.f("ix_monitor_endpoints_http_method"), "monitor_endpoints", ["http_method"], unique=False)
    op.create_index(op.f("ix_monitor_endpoints_id"), "monitor_endpoints", ["id"], unique=False)
    op.create_index(op.f("ix_monitor_endpoints_url"), "monitor_endpoints", ["url"], unique=False)
    op.create_table(
        "monitor_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("endpoint_id", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("response_size", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["endpoint_id"], ["monitor_endpoints.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("http_status >= 100", name="ck_monitor_result_status_min"),
        sa.CheckConstraint("http_status <= 599", name="ck_monitor_result_status_max"),
        sa.CheckConstraint("latency_ms >= 0", name="ck_monitor_result_latency_non_negative"),
        sa.CheckConstraint("response_size >= 0", name="ck_monitor_result_response_size_non_negative"),
    )
    op.create_index(op.f("ix_monitor_results_endpoint_id"), "monitor_results", ["endpoint_id"], unique=False)
    op.create_index(op.f("ix_monitor_results_error_category"), "monitor_results", ["error_category"], unique=False)
    op.create_index(op.f("ix_monitor_results_id"), "monitor_results", ["id"], unique=False)
    op.create_index(op.f("ix_monitor_results_observed_at"), "monitor_results", ["observed_at"], unique=False)
    op.create_index(op.f("ix_monitor_results_success"), "monitor_results", ["success"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_monitor_results_success"), table_name="monitor_results")
    op.drop_index(op.f("ix_monitor_results_observed_at"), table_name="monitor_results")
    op.drop_index(op.f("ix_monitor_results_id"), table_name="monitor_results")
    op.drop_index(op.f("ix_monitor_results_error_category"), table_name="monitor_results")
    op.drop_index(op.f("ix_monitor_results_endpoint_id"), table_name="monitor_results")
    op.drop_table("monitor_results")
    op.drop_index(op.f("ix_monitor_endpoints_url"), table_name="monitor_endpoints")
    op.drop_index(op.f("ix_monitor_endpoints_id"), table_name="monitor_endpoints")
    op.drop_index(op.f("ix_monitor_endpoints_http_method"), table_name="monitor_endpoints")
    op.drop_index(op.f("ix_monitor_endpoints_active"), table_name="monitor_endpoints")
    op.drop_table("monitor_endpoints")
