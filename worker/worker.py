import os

from arq.connections import RedisSettings
from dotenv import load_dotenv

from jobs.example import example_job


load_dotenv()

REDIS_URL = os.environ["REDIS_URL"]


async def startup(ctx):
    print("Sentinel worker started")


async def shutdown(ctx):
    print("Sentinel worker stopped")


class WorkerSettings:
    functions = [example_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(REDIS_URL)