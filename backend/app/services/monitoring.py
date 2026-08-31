from __future__ import annotations

import asyncio
import ipaddress
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


@dataclass(slots=True)
class MonitoringCheckResult:
    endpoint_id: int | None
    url: str
    http_status: int | None
    latency_ms: int
    response_size: int
    success: bool
    error_category: str | None = None
    error_details: str | None = None


@dataclass(slots=True)
class MonitorJob:
    endpoint_id: int | None
    url: str
    method: str = "GET"
    expected_status_code: int = 200
    timeout_seconds: int = 10
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5
    allow_localhost: bool = False


def validate_monitor_url(raw_url: str, *, allow_localhost: bool = False) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are allowed.")
    if not parsed.hostname:
        raise ValueError("URL does not include a hostname.")

    hostname = parsed.hostname.lower()
    blocked_hosts = {
        "localhost",
        "localhost.localdomain",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "169.254.169.254",
        "metadata.google.internal",
        "metadata",
    }
    if hostname in blocked_hosts or hostname.endswith(".localhost"):
        if allow_localhost and hostname in {"localhost", "127.0.0.1", "::1"}:
            return raw_url
        raise ValueError("Local and metadata targets are not allowed.")

    try:
        ip_addresses = _resolve_host_addresses(hostname)
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed for host: {hostname}") from exc

    for address in ip_addresses:
        if _is_dangerous_ip(address) and not (allow_localhost and address.is_loopback):
            raise ValueError(f"Blocked internal or unroutable target: {hostname}")

    return raw_url


def _resolve_host_addresses(hostname: str) -> set[ipaddress._BaseAddress]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise

    addresses: set[ipaddress._BaseAddress] = set()
    for info in infos:
        ip_text = info[4][0]
        try:
            addresses.add(ipaddress.ip_address(ip_text))
        except ValueError:
            continue
    return addresses


def _is_dangerous_ip(address: ipaddress._BaseAddress) -> bool:
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or address.is_site_local
    ):
        return True
    return False


async def perform_monitor_check(job: MonitorJob) -> MonitoringCheckResult:
    assert job.url
    try:
        validate_monitor_url(job.url, allow_localhost=job.allow_localhost)
    except ValueError as exc:
        return MonitoringCheckResult(
            endpoint_id=job.endpoint_id,
            url=job.url,
            http_status=None,
            latency_ms=0,
            response_size=0,
            success=False,
            error_category="invalid_url",
            error_details=str(exc),
        )

    started_at = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            follow_redirects=False, timeout=job.timeout_seconds
        ) as client:
            response = await client.request(job.method, job.url)
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            response_size = len(response.content)

            if response.is_redirect:
                return MonitoringCheckResult(
                    endpoint_id=job.endpoint_id,
                    url=job.url,
                    http_status=response.status_code,
                    latency_ms=latency_ms,
                    response_size=response_size,
                    success=False,
                    error_category="redirect_not_allowed",
                    error_details="Redirect responses are not allowed for monitoring checks.",
                )

            success = response.status_code == job.expected_status_code
            error_category = None
            error_details = None
            if not success:
                error_category = "unexpected_status"
                error_details = (
                    f"Expected HTTP {job.expected_status_code}, "
                    f"received HTTP {response.status_code}."
                )

            return MonitoringCheckResult(
                endpoint_id=job.endpoint_id,
                url=job.url,
                http_status=response.status_code,
                latency_ms=latency_ms,
                response_size=response_size,
                success=success,
                error_category=error_category,
                error_details=error_details,
            )
    except httpx.TimeoutException as exc:
        return MonitoringCheckResult(
            endpoint_id=job.endpoint_id,
            url=job.url,
            http_status=None,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            response_size=0,
            success=False,
            error_category="timeout",
            error_details=str(exc),
        )
    except httpx.ConnectError as exc:
        return MonitoringCheckResult(
            endpoint_id=job.endpoint_id,
            url=job.url,
            http_status=None,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            response_size=0,
            success=False,
            error_category="connection_error",
            error_details=str(exc),
        )
    except httpx.DNSError as exc:
        return MonitoringCheckResult(
            endpoint_id=job.endpoint_id,
            url=job.url,
            http_status=None,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            response_size=0,
            success=False,
            error_category="dns_error",
            error_details=str(exc),
        )
    except httpx.InvalidURL as exc:
        return MonitoringCheckResult(
            endpoint_id=job.endpoint_id,
            url=job.url,
            http_status=None,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            response_size=0,
            success=False,
            error_category="invalid_url",
            error_details=str(exc),
        )
    except httpx.HTTPError as exc:
        return MonitoringCheckResult(
            endpoint_id=job.endpoint_id,
            url=job.url,
            http_status=None,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            response_size=0,
            success=False,
            error_category="http_error",
            error_details=str(exc),
        )


class MonitoringWorker:
    def __init__(
        self,
        *,
        max_concurrency: int = 4,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self._queue: asyncio.Queue[MonitorJob] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._seen_jobs: set[str] = set()

    async def enqueue(self, job: MonitorJob) -> bool:
        dedupe_key = f"{job.endpoint_id}:{job.url}:{job.method}:{job.expected_status_code}:{job.timeout_seconds}"
        if dedupe_key in self._seen_jobs:
            return False
        self._seen_jobs.add(dedupe_key)
        await self._queue.put(job)
        return True

    async def run_job(self, job: MonitorJob) -> MonitoringCheckResult:
        attempt = 0
        while True:
            result = await perform_monitor_check(job)
            if result.success or attempt >= job.max_retries:
                return result
            attempt += 1
            await asyncio.sleep(job.retry_backoff_seconds * (2 ** (attempt - 1)))

    async def process(self) -> list[MonitoringCheckResult]:
        results: list[MonitoringCheckResult] = []
        while not self._queue.empty():
            job = await self._queue.get()
            async with self._semaphore:
                results.append(await self.run_job(job))
            self._queue.task_done()
        return results


__all__ = [
    "MonitorJob",
    "MonitoringCheckResult",
    "MonitoringWorker",
    "perform_monitor_check",
    "validate_monitor_url",
]
