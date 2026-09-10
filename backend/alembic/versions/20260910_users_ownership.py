"""Add users and assign existing monitors to the migration admin."""

from alembic import op
import bcrypt
import os
import sqlalchemy as sa

revision = "20260910_users_ownership"
down_revision = "20260909_alert_deliveries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    email = os.getenv("ADMIN_EMAIL", "admin@nexus.local").lower()
    password = os.getenv("ADMIN_PASSWORD", "change-me-immediately")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "INSERT INTO users (email, hashed_password, created_at) "
            "VALUES (:email, :password, CURRENT_TIMESTAMP)"
        ),
        {"email": email, "password": hashed},
    )
    user_id = connection.execute(sa.text("SELECT id FROM users WHERE email = :email"), {"email": email}).scalar_one()

    op.add_column("monitor_endpoints", sa.Column("owner_id", sa.Integer(), nullable=True))
    connection.execute(sa.text("UPDATE monitor_endpoints SET owner_id = :owner_id"), {"owner_id": user_id})
    with op.batch_alter_table("monitor_endpoints") as batch_op:
        batch_op.alter_column("owner_id", nullable=False)
    op.create_foreign_key("fk_monitor_endpoints_owner_id_users", "monitor_endpoints", "users", ["owner_id"], ["id"])
    op.create_index("ix_monitor_endpoints_owner_id", "monitor_endpoints", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_monitor_endpoints_owner_id", table_name="monitor_endpoints")
    op.drop_constraint("fk_monitor_endpoints_owner_id_users", "monitor_endpoints", type_="foreignkey")
    op.drop_column("monitor_endpoints", "owner_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
