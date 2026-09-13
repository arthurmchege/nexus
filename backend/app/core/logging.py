import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "event",
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "user_id",
            "monitor_id",
            "incident_id",
            "incident_event",
            "http_status",
            "success",
            "count",
            "attempt",
            "retry_after",
            "email_domain",
            "rate_limit_key",
            "environment",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, default=str, sort_keys=True)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("nexus")
    logger.setLevel(settings.log_level.upper())

    if logger.handlers:
        return logger

    formatter = JsonFormatter()
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


logger: logging.Logger = setup_logging()
