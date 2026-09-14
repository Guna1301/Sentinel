from fastapi import FastAPI

app = FastAPI(
    title="Sentinel API",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "sentinel-api",
    }
