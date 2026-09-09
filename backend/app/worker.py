from __future__ import annotations

import asyncio

from app.core.logging import logger
from app.core.redis_client import redis_client
from app.db.session import SessionLocal
from app.services.monitoring_pipeline import process_queued_monitoring_job
from app.services.redis_queue import MonitoringQueue
from app.services.scheduler import MonitorScheduler

SCHEDULER_POLL_SECONDS = 1.0
IDLE_POLL_SECONDS = 0.25


async def run_monitoring_worker() -> None:
    """Continuously schedule due monitors and consume their Redis jobs."""
    queue = MonitoringQueue(redis_client=redis_client)
    scheduler = MonitorScheduler(SessionLocal, queue)
    logger.info("NEXUS monitoring worker started")

    while True:
        claimed = await asyncio.to_thread(scheduler.claim_due_monitors)
        if claimed:
            logger.info("Queued %d due monitor checks", len(claimed))

        result = await process_queued_monitoring_job(
            queue,
            session_factory=SessionLocal,
        )
        if result is None:
            await asyncio.sleep(SCHEDULER_POLL_SECONDS)
        else:
            await asyncio.sleep(IDLE_POLL_SECONDS)


def main() -> None:
    asyncio.run(run_monitoring_worker())


if __name__ == "__main__":
    main()
