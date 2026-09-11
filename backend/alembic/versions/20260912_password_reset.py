"""Add password reset session invalidation timestamp."""

import sqlalchemy as sa

from alembic import op

revision = "20260912_password_reset"
down_revision = "20260910_users_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
