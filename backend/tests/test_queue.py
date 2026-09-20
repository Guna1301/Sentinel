import pytest

from app.core.queue import QueueClient


class FakeQueue:
    def __init__(self):
        self.calls = []

    async def enqueue_job(self, job_name, *args, **kwargs):
        self.calls.append(
            {
                "job_name": job_name,
                "args": args,
                "kwargs": kwargs,
            }
        )

        return "fake-job-id"


@pytest.mark.asyncio
async def test_enqueue_delegates_to_arq_pool():
    fake_pool = FakeQueue()
    queue = QueueClient(fake_pool)

    result = await queue.enqueue(
        "example_job",
        "hello",
        value=42,
    )

    assert result == "fake-job-id"

    assert fake_pool.calls == [
        {
            "job_name": "example_job",
            "args": ("hello",),
            "kwargs": {"value": 42},
        }
    ]