import json
import logging

from app.core.logging import JsonFormatter


def test_log_output_is_json_and_excludes_sensitive_fields(caplog) -> None:
    caplog.set_level(logging.INFO, logger="nexus")
    secret = "super-secret-password"
    token = "eyJfull-jwt-token"

    logging.getLogger("nexus").info(
        "safe auth event",
        extra={
            "event": "auth_test",
            "password": secret,
            "token": token,
        },
    )

    record = caplog.records[-1]
    rendered = JsonFormatter().format(record)
    payload = json.loads(rendered)
    assert payload["event"] == "auth_test"
    assert secret not in rendered
    assert token not in rendered
    assert "password" not in payload
    assert "token" not in payload


def test_auth_failure_is_structured(caplog) -> None:
    caplog.set_level(logging.INFO, logger="nexus")
    logging.getLogger("nexus").warning(
        "User login failed",
        extra={"event": "auth_login_failure", "email_domain": "example.com"},
    )

    assert any(record.event == "auth_login_failure" for record in caplog.records)
