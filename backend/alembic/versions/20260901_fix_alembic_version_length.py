"""Widen Alembic version metadata to support long revision IDs.

Revision ID: 20260901_fix_alembic_version_length
Revises: 20240831_monitoring_models
Create Date: 2026-09-01 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260901_fix_alembic_version_length"
down_revision = "20240831_monitoring_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(32)")
