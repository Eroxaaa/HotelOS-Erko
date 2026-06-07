# Maintenance Service v1.0

from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from database import init_db, seed_db, AsyncSessionLocal
from redis_client import broker, Channels


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[MAINTENANCE] Servis ishga tushmoqda...")

    await init_db()

    async with AsyncSessionLocal() as session:
        await seed_db(session)

    broker.start()

    print("[MAINTENANCE] Servis tayyor")

    yield

    print("[MAINTENANCE] Servis to'xtatilmoqda...")


app = FastAPI(
    title="HotelOS — Maintenance Service",
    description="GrandStay mehmonxonasi texnik xizmat servisi",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api/maintenance", tags=["Maintenance"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "maintenance-service"}