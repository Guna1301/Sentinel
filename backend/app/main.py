import os

import httpx

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.queue import QueueClient, create_redis_pool

from app.api.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    arq_pool = await create_redis_pool()

    http_client = httpx.AsyncClient(timeout=10.0)

    app.state.http_client = http_client
    app.state.queue = QueueClient(arq_pool)

    yield

    await http_client.aclose()
    await arq_pool.aclose()


app = FastAPI(
    title="Sentinel API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "sentinel-api",
        "instance": os.getenv("HOSTNAME", "unknown"),
    }