import pytest

from app.core.queue import QueueClient, create_redis_pool


@pytest.mark.asyncio
async def test_example_job_executes_through_redis():
    pool = await create_redis_pool()
    queue = QueueClient(pool)

    try:
        job = await queue.enqueue(
            "example_job",
            "hello from Sentinel",
        )

        result = await job.result(timeout=10)

        assert result == "hello from Sentinel"

    finally:
        await pool.aclose()