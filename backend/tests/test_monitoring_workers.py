from __future__ import annotations

import contextlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.services.monitoring import (
    MonitoringWorker,
    MonitorJob,
    perform_monitor_check,
    validate_monitor_url,
)


@contextlib.contextmanager
def mock_http_server(
    status_code: int = 200,
    body: str = "ok",
    delay_seconds: float = 0.0,
    *,
    fail_first_request: bool = False,
):
    request_count = {"count": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            request_count["count"] += 1
            if fail_first_request and request_count["count"] == 1:
                self.send_response(503)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if delay_seconds:
                import time

                time.sleep(delay_seconds)
            self.send_response(status_code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body.encode("utf-8"))))
            self.end_headers()
            try:
                self.wfile.write(body.encode("utf-8"))
            except BrokenPipeError:
                return

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.asyncio
async def test_successful_health_check() -> None:
    with mock_http_server(status_code=200, body="healthy") as target_url:
        job = MonitorJob(
            endpoint_id=1,
            url=target_url,
            method="GET",
            expected_status_code=200,
            allow_localhost=True,
        )
        result = await perform_monitor_check(job)

    assert result.success is True
    assert result.http_status == 200
    assert result.error_category is None
    assert result.response_size > 0


@pytest.mark.asyncio
async def test_unexpected_http_status() -> None:
    with mock_http_server(status_code=503, body="down") as target_url:
        job = MonitorJob(
            endpoint_id=2,
            url=target_url,
            method="GET",
            expected_status_code=200,
            allow_localhost=True,
        )
        result = await perform_monitor_check(job)

    assert result.success is False
    assert result.http_status == 503
    assert result.error_category == "unexpected_status"


@pytest.mark.asyncio
async def test_timeout_failure() -> None:
    with mock_http_server(status_code=200, delay_seconds=1.5) as target_url:
        job = MonitorJob(
            endpoint_id=3,
            url=target_url,
            method="GET",
            expected_status_code=200,
            timeout_seconds=1,
            allow_localhost=True,
        )
        result = await perform_monitor_check(job)

    assert result.success is False
    assert result.error_category == "timeout"


@pytest.mark.asyncio
async def test_connection_failure() -> None:
    job = MonitorJob(
        endpoint_id=4,
        url="http://127.0.0.1:65535/",
        method="GET",
        expected_status_code=200,
        timeout_seconds=1,
        allow_localhost=True,
    )
    result = await perform_monitor_check(job)

    assert result.success is False
    assert result.error_category == "connection_error"


@pytest.mark.asyncio
async def test_dns_failure() -> None:
    job = MonitorJob(
        endpoint_id=5,
        url="http://nexus.invalid/",
        method="GET",
        expected_status_code=200,
        timeout_seconds=1,
    )
    result = await perform_monitor_check(job)

    assert result.success is False
    assert result.error_category in {"dns_error", "invalid_url"}


@pytest.mark.asyncio
async def test_retry_behavior() -> None:
    worker = MonitoringWorker(max_concurrency=1, max_retries=1, retry_backoff_seconds=0.05)
    with mock_http_server(status_code=200, body="recovered", fail_first_request=True) as target_url:
        job = MonitorJob(
            endpoint_id=6,
            url=target_url,
            method="GET",
            expected_status_code=200,
            allow_localhost=True,
        )
        result = await worker.run_job(job)

    assert result.success is True
    assert result.http_status == 200


@pytest.mark.asyncio
async def test_worker_failure_behavior() -> None:
    worker = MonitoringWorker(max_concurrency=1)
    job = MonitorJob(endpoint_id=7, url="http://localhost:8000/", method="GET")
    result = await worker.run_job(job)

    assert result.success is False
    assert result.error_category == "invalid_url"


@pytest.mark.parametrize(
    "value",
    [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://[::1]:8000",
        "http://169.254.169.254/latest/meta-data",
        "ftp://example.com",
    ],
)
def test_invalid_dangerous_urls(value: str) -> None:
    with pytest.raises(ValueError):
        validate_monitor_url(value)


@pytest.mark.asyncio
async def test_concurrent_monitoring_behavior() -> None:
    with (
        mock_http_server(status_code=200, body="one") as first_url,
        mock_http_server(status_code=200, body="two") as second_url,
        mock_http_server(status_code=200, body="three") as third_url,
    ):
        worker = MonitoringWorker(max_concurrency=2, max_retries=0, retry_backoff_seconds=0.01)
        await worker.enqueue(
            MonitorJob(
                endpoint_id=8,
                url=first_url,
                expected_status_code=200,
                allow_localhost=True,
            )
        )
        await worker.enqueue(
            MonitorJob(
                endpoint_id=9,
                url=second_url,
                expected_status_code=200,
                allow_localhost=True,
            )
        )
        await worker.enqueue(
            MonitorJob(
                endpoint_id=10,
                url=third_url,
                expected_status_code=200,
                allow_localhost=True,
            )
        )
        results = await worker.process()

    assert len(results) == 3
    assert all(item.success for item in results)
