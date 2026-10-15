
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from dotenv import load_dotenv
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

from db.database import engine
from db.scheduling import (
    advance_monitoring_schedule,
    get_due_monitoring_configs,
)


REDIS_URL = os.environ["REDIS_URL"]

POLL_INTERVAL_SECONDS = 5
BATCH_SIZE = 100

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sentinel.scheduler")


def build_scheduled_job_id(
    config_id: UUID,
    scheduled_for: datetime,
) -> str:
    timestamp = scheduled_for.astimezone(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%S%fZ")

    return f"monitor-{config_id}-{timestamp}"


async def process_due_checks(
    redis_pool: ArqRedis,
) -> int:
    now = datetime.now(timezone.utc)

    configs = await get_due_monitoring_configs(
        now=now,
        limit=BATCH_SIZE,
    )

    advanced_count = 0

    for config in configs:
        config_id = config["id"]
        scheduled_for = config["next_check_at"]

        job_id = build_scheduled_job_id(
            config_id,
            scheduled_for,
        )

        try:
            job = await redis_pool.enqueue_job(
                "check_monitor",
                str(config_id),
                _job_id=job_id,
            )
        except RedisError:
            # Keep the schedule due so a later poll can retry.
            logger.exception(
                "Failed to enqueue monitoring check "
                "for config_id=%s",
                config_id,
            )
            continue

        next_check_at = (
            datetime.now(timezone.utc)
            + timedelta(
                seconds=config["interval_seconds"],
            )
        )

        advanced = await advance_monitoring_schedule(
            config_id=config_id,
            expected_next_check_at=scheduled_for,
            next_check_at=next_check_at,
        )

        if not advanced:
            logger.info(
                "Schedule changed while processing config_id=%s",
                config_id,
            )
            continue

        advanced_count += 1

        if job is None:
            logger.info(
                "Scheduled job already exists; advanced schedule "
                "for config_id=%s job_id=%s",
                config_id,
                job_id,
            )
        else:
            logger.info(
                "Enqueued scheduled monitoring check "
                "config_id=%s job_id=%s",
                config_id,
                job_id,
            )

    return advanced_count


async def create_redis_pool_with_retry() -> ArqRedis:
    while True:
        try:
            return await create_pool(
                RedisSettings.from_dsn(REDIS_URL),
            )
        except RedisError:
            logger.exception(
                "Redis unavailable during scheduler startup; retrying"
            )
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def main() -> None:
    redis_pool = await create_redis_pool_with_retry()

    logger.info(
        "Sentinel scheduler started; poll_interval_seconds=%s",
        POLL_INTERVAL_SECONDS,
    )

    try:
        while True:
            try:
                advanced_count = await process_due_checks(redis_pool)

                if advanced_count:
                    logger.info(
                        "Advanced %s monitoring schedules",
                        advanced_count,
                    )

            except (RedisError, SQLAlchemyError):
                logger.exception(
                    "Scheduler iteration failed; retrying next poll"
                )

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    finally:
        await redis_pool.aclose()
        await engine.dispose()
        logger.info("Sentinel scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
