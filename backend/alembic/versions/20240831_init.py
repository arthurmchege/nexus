"""Initial NEXUS schema

Revision ID: 20240831_init
Revises:
Create Date: 2024-08-31 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20240831_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "health_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_health_checks_name"), "health_checks", ["name"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_health_checks_name"), table_name="health_checks")
    op.drop_table("health_checks")
