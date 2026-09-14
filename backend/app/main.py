from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.queue import create_redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.arq_pool = await create_redis_pool()

    yield

    await app.state.arq_pool.close()


app = FastAPI(
    title="Sentinel API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "sentinel-api",
    }