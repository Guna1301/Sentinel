from fastapi import FastAPI

app = FastAPI(title="Sentinel API")


@app.get("/health")
async def health():
    return {"status": "ok"}