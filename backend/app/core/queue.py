import os

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ["REDIS_URL"]


async def create_redis_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(REDIS_URL))