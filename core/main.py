from fastapi import FastAPI
from core.routes import router

app = FastAPI(title="MIRRORNODE Hermes", version="0.2.0")
app.include_router(router)

@app.get("/health")
async def health():
    return {"node": "hermes", "status": "alive", "version": "0.2.0"}
