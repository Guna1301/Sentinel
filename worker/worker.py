from arq import create_pool
from arq.connections import RedisSettings
import os

from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ["REDIS_URL"]


async def startup(ctx):
    print("Sentinel worker started")


async def shutdown(ctx):
    print("Sentinel worker stopped")


async def example_job(ctx):
    print("Example job executed")


class WorkerSettings:
    functions = [example_job]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings.from_dsn(REDIS_URL)