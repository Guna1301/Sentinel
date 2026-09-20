import os

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from dotenv import load_dotenv


load_dotenv()

REDIS_URL = os.environ["REDIS_URL"]


async def create_redis_pool() -> ArqRedis:
    return await create_pool(
        RedisSettings.from_dsn(REDIS_URL)
    )


class QueueClient:
    def __init__(self, pool: ArqRedis):
        self._pool = pool

    async def enqueue(self,job_name: str,*args,**kwargs,):
        return await self._pool.enqueue_job(
            job_name,
            *args,
            **kwargs,
        )