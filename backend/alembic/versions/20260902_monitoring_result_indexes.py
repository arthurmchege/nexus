"""Add query-oriented indexes for monitor result reads.

Revision ID: 20260902_monitoring_result_indexes
Revises: 20260901_monitoring_scheduler_claim_locking
Create Date: 2026-09-02 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260902_monitoring_result_indexes"
down_revision = "20260901_monitoring_scheduler_claim_locking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_monitor_results_endpoint_observed_at",
        "monitor_results",
        ["endpoint_id", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_monitor_results_partition_endpoint_observed",
        "monitor_results",
        ["partition_bucket", "endpoint_id", "observed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_monitor_results_partition_endpoint_observed", table_name="monitor_results")
    op.drop_index("ix_monitor_results_endpoint_observed_at", table_name="monitor_results")
