"""Add the read-only public demo account and representative monitoring data."""

from datetime import datetime, timedelta

import bcrypt
import sqlalchemy as sa

from alembic import op

revision = "20260913_demo_account"
down_revision = "20260912_password_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    connection = op.get_bind()
    demo_email = "demo@nexus.local"
    demo_password = bcrypt.hashpw(b"demo-read-only", bcrypt.gensalt()).decode()
    connection.execute(
        sa.text(
            "INSERT INTO users (email, hashed_password, created_at, is_demo) "
            "VALUES (:email, :password, :created_at, :is_demo)"
        ),
        {
            "email": demo_email,
            "password": demo_password,
            "created_at": datetime.utcnow(),
            "is_demo": True,
        },
    )
    demo_id = connection.execute(
        sa.text("SELECT id FROM users WHERE email = :email"), {"email": demo_email}
    ).scalar_one()

    now = datetime.utcnow()
    monitors = [
        ("https://api.github.com/nexus-demo", "up", True),
        ("https://httpstat.us/503?nexus_demo=1", "down", True),
        ("https://httpstat.us/429?nexus_demo=1", "degraded", True),
        ("https://example.com/nexus-demo", "up", False),
    ]
    monitor_ids: list[int] = []
    for index, (url, health_state, active) in enumerate(monitors):
        connection.execute(
            sa.text(
                "INSERT INTO monitor_endpoints "
                "(owner_id, url, http_method, expected_status_code, interval_seconds, "
                "timeout_seconds, active, health_state, consecutive_failures, "
                "consecutive_successes, failure_threshold, recovery_threshold, "
                "next_check_at, last_check_at, created_at, updated_at) "
                "VALUES (:owner_id, :url, 'GET', 200, 60, 10, :active, :health_state, "
                ":failures, :successes, 2, 2, :next_check_at, :last_check_at, "
                ":created_at, :updated_at)"
            ),
            {
                "owner_id": demo_id,
                "url": url,
                "active": active,
                "health_state": health_state,
                "failures": 3 if health_state == "down" else 1 if health_state == "degraded" else 0,
                "successes": 0 if health_state != "up" else 5,
                "next_check_at": now + timedelta(minutes=5),
                "last_check_at": now - timedelta(minutes=index + 1),
                "created_at": now - timedelta(days=14 - index),
                "updated_at": now - timedelta(minutes=index + 1),
            },
        )
        monitor_ids.append(
            connection.execute(
                sa.text(
                    "SELECT id FROM monitor_endpoints " "WHERE owner_id = :owner_id AND url = :url"
                ),
                {"owner_id": demo_id, "url": url},
            ).scalar_one()
        )

    for monitor_id, health_state in zip(monitor_ids, [True, False, False, True], strict=True):
        for offset in range(6):
            observed_at = now - timedelta(hours=offset + 1)
            success = health_state if offset < 2 else True
            connection.execute(
                sa.text(
                    "INSERT INTO monitor_results "
                    "(endpoint_id, observed_at, partition_bucket, http_status, latency_ms, "
                    "response_size, success, error_category, error_details) "
                    "VALUES (:endpoint_id, :observed_at, :partition_bucket, :http_status, "
                    ":latency_ms, :response_size, :success, :error_category, :error_details)"
                ),
                {
                    "endpoint_id": monitor_id,
                    "observed_at": observed_at,
                    "partition_bucket": observed_at.strftime("%Y-%m"),
                    "http_status": 200 if success else 503,
                    "latency_ms": 120 + offset * 12 if success else 860 + offset * 20,
                    "response_size": 2048 if success else 0,
                    "success": success,
                    "error_category": None if success else "unexpected_status",
                    "error_details": None if success else "Demo incident sample",
                },
            )

    connection.execute(
        sa.text(
            "INSERT INTO incidents "
            "(monitor_id, opened_at, resolved_at, trigger_reason, status) "
            "VALUES (:monitor_id, :opened_at, NULL, :reason, 'open')"
        ),
        {
            "monitor_id": monitor_ids[1],
            "opened_at": now - timedelta(hours=3),
            "reason": "Three consecutive HTTP 503 responses",
        },
    )
    incident_id = connection.execute(
        sa.text("SELECT id FROM incidents WHERE monitor_id = :monitor_id AND status = 'open'"),
        {"monitor_id": monitor_ids[1]},
    ).scalar_one()
    connection.execute(
        sa.text(
            "INSERT INTO alert_deliveries "
            "(incident_id, event, channel, status, attempts, last_error, created_at) "
            "VALUES (:incident_id, 'opened', 'webhook', 'delivered', 1, NULL, :created_at)"
        ),
        {"incident_id": incident_id, "created_at": now - timedelta(hours=3)},
    )

    connection.execute(
        sa.text(
            "INSERT INTO incidents "
            "(monitor_id, opened_at, resolved_at, trigger_reason, status) "
            "VALUES (:monitor_id, :opened_at, :resolved_at, :reason, 'resolved')"
        ),
        {
            "monitor_id": monitor_ids[2],
            "opened_at": now - timedelta(days=1),
            "resolved_at": now - timedelta(hours=20),
            "reason": "Repeated HTTP 429 responses",
        },
    )
    resolved_id = connection.execute(
        sa.text("SELECT id FROM incidents WHERE monitor_id = :monitor_id AND status = 'resolved'"),
        {"monitor_id": monitor_ids[2]},
    ).scalar_one()
    connection.execute(
        sa.text(
            "INSERT INTO alert_deliveries "
            "(incident_id, event, channel, status, attempts, delivered_at, created_at) "
            "VALUES (:incident_id, 'resolved', 'webhook', 'delivered', 1, :delivered_at, :created_at)"
        ),
        {
            "incident_id": resolved_id,
            "delivered_at": now - timedelta(hours=20),
            "created_at": now - timedelta(hours=20),
        },
    )


def downgrade() -> None:
    connection = op.get_bind()
    demo_id = connection.execute(
        sa.text("SELECT id FROM users WHERE email = 'demo@nexus.local'")
    ).scalar()
    if demo_id is not None:
        monitor_ids = [
            row[0]
            for row in connection.execute(
                sa.text("SELECT id FROM monitor_endpoints WHERE owner_id = :owner_id"),
                {"owner_id": demo_id},
            )
        ]
        if monitor_ids:
            connection.execute(
                sa.text(
                    "DELETE FROM alert_deliveries WHERE incident_id IN "
                    "(SELECT id FROM incidents WHERE monitor_id IN :monitor_ids)"
                ).bindparams(sa.bindparam("monitor_ids", expanding=True)),
                {"monitor_ids": monitor_ids},
            )
            connection.execute(
                sa.text("DELETE FROM incidents WHERE monitor_id IN :monitor_ids").bindparams(
                    sa.bindparam("monitor_ids", expanding=True)
                ),
                {"monitor_ids": monitor_ids},
            )
            connection.execute(
                sa.text("DELETE FROM monitor_results WHERE endpoint_id IN :monitor_ids").bindparams(
                    sa.bindparam("monitor_ids", expanding=True)
                ),
                {"monitor_ids": monitor_ids},
            )
            connection.execute(
                sa.text("DELETE FROM monitor_endpoints WHERE id IN :monitor_ids").bindparams(
                    sa.bindparam("monitor_ids", expanding=True)
                ),
                {"monitor_ids": monitor_ids},
            )
        connection.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": demo_id})
    op.drop_column("users", "is_demo")
