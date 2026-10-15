
import os

# These tests mock database access and never connect to PostgreSQL or Redis.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/test",
)
os.environ.setdefault(
    "REDIS_URL",
    "redis://127.0.0.1:6379",
)

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from redis.exceptions import RedisError

import scheduler


CONFIG_ID = UUID("11111111-1111-4111-8111-111111111111")


class FakeRedisPool:
    def __init__(self, *, result="queued", error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def enqueue_job(self, job_name, *args, **kwargs):
        self.calls.append(
            {
                "job_name": job_name,
                "args": args,
                "kwargs": kwargs,
            }
        )

        if self.error is not None:
            raise self.error

        return self.result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "existing_job",
    [False, True],
    ids=["new-job", "duplicate-job"],
)
async def test_due_config_uses_deterministic_job_id_and_advances(
    monkeypatch,
    existing_job,
):
    scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=20)

    config = {
        "id": CONFIG_ID,
        "interval_seconds": 60,
        "next_check_at": scheduled_for,
    }

    async def fake_get_due(*, now, limit):
        assert limit == scheduler.BATCH_SIZE
        return [config]

    advanced = []

    async def fake_advance(**kwargs):
        advanced.append(kwargs)
        return True

    monkeypatch.setattr(
        scheduler,
        "get_due_monitoring_configs",
        fake_get_due,
    )
    monkeypatch.setattr(
        scheduler,
        "advance_monitoring_schedule",
        fake_advance,
    )

    pool = FakeRedisPool(
        result=None if existing_job else "queued",
    )

    before_processing = datetime.now(timezone.utc)

    processed = await scheduler.process_due_checks(pool)

    after_processing = datetime.now(timezone.utc)

    expected_job_id = scheduler.build_scheduled_job_id(
        CONFIG_ID,
        scheduled_for,
    )

    assert processed == 1
    assert pool.calls == [
        {
            "job_name": "check_monitor",
            "args": (str(CONFIG_ID),),
            "kwargs": {"_job_id": expected_job_id},
        }
    ]

    assert len(advanced) == 1
    assert advanced[0]["config_id"] == CONFIG_ID
    assert advanced[0]["expected_next_check_at"] == scheduled_for
    next_check_at = advanced[0]["next_check_at"]
    interval = timedelta(seconds=config["interval_seconds"])

    assert (
        before_processing + interval
        <= next_check_at
        <= after_processing + interval
    )


@pytest.mark.asyncio
async def test_redis_failure_does_not_advance_schedule(monkeypatch):
    scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=1)

    async def fake_get_due(*, now, limit):
        return [
            {
                "id": CONFIG_ID,
                "interval_seconds": 60,
                "next_check_at": scheduled_for,
            }
        ]

    async def unexpected_advance(**kwargs):
        pytest.fail("Schedule must not advance when enqueue fails")

    monkeypatch.setattr(
        scheduler,
        "get_due_monitoring_configs",
        fake_get_due,
    )
    monkeypatch.setattr(
        scheduler,
        "advance_monitoring_schedule",
        unexpected_advance,
    )

    pool = FakeRedisPool(
        error=RedisError("Redis unavailable"),
    )

    assert await scheduler.process_due_checks(pool) == 0
    assert len(pool.calls) == 1
@pytest.mark.asyncio
async def test_stale_schedule_update_is_not_counted_as_advanced(
    monkeypatch,
):
    scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=5)

    config = {
        "id": CONFIG_ID,
        "interval_seconds": 60,
        "next_check_at": scheduled_for,
    }

    async def fake_get_due(*, now, limit):
        return [config]

    async def fake_advance(**kwargs):
        assert kwargs["config_id"] == CONFIG_ID
        assert kwargs["expected_next_check_at"] == scheduled_for
        return False

    monkeypatch.setattr(
        scheduler,
        "get_due_monitoring_configs",
        fake_get_due,
    )
    monkeypatch.setattr(
        scheduler,
        "advance_monitoring_schedule",
        fake_advance,
    )

    pool = FakeRedisPool(result="queued")

    processed = await scheduler.process_due_checks(pool)

    # The job may already be enqueued, but the stale schedule
    # was not successfully advanced.
    assert processed == 0
    assert len(pool.calls) == 1