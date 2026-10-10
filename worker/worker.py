import os

import httpx
from arq.connections import RedisSettings
from dotenv import load_dotenv

from clients.http import HttpCheckClient
from db.database import engine
from jobs.example import example_job
from jobs.failure import (
    always_fail_job,
    retry_job,
    slow_job,
)
from jobs.monitoring import check_monitor


load_dotenv()

REDIS_URL = os.environ["REDIS_URL"]


async def startup(ctx):
    http_client = httpx.AsyncClient()

    ctx["http_client"] = http_client
    ctx["http_check_client"] = HttpCheckClient(http_client)

    print("Sentinel worker started")


async def shutdown(ctx):
    http_client = ctx.pop("http_client", None)

    try:
        if http_client is not None:
            await http_client.aclose()
    finally:
        await engine.dispose()
        print("Sentinel worker stopped")


class WorkerSettings:
    functions = [
        example_job,
        slow_job,
        always_fail_job,
        retry_job,
        check_monitor,
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings.from_dsn(REDIS_URL)

    job_timeout = 30
    max_tries = 3
    retry_jobs = True