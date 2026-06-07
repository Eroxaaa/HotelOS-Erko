# Reception Service v1.0 

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from database import init_db, seed_db, AsyncSessionLocal
from redis_client import broker

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI ishga tushganda va to'xtaganda bajariladigan amallar.
    startup: DB jadvallar yaratiladi, seed yuklanadi, broker ishga tushadi.
    shutdown: ulanishlar yopiladi.
    """

    # Startup
    print("[RECEPTION] Servis ishga tushmoqda...")

    # Jadvallar yaratish
    await init_db()

    # Namuna ma'lumotlar yuklash
    async with AsyncSessionLocal() as session:
        await seed_db(session)

    # Cleaning servisidan "xona tozalandi" xabarini tinglash
    from redis_client import Channels
    from datetime import datetime
    from sqlalchemy import update
    from database import RoomModel
    from models import RoomStatus

    async def on_room_cleaned(data: dict):
        """
        Cleaning servis xonani tozalaganda bu funksiya chaqiriladi.
        Xona holati Clean ga o'zgartiriladi.
        """
        room_number = data.get("room_number")
        if not room_number:
            return

        async with AsyncSessionLocal() as session:
            await session.execute(
                update(RoomModel)
                .where(RoomModel.room_number == room_number)
                .values(
                    status=RoomStatus.CLEAN,
                    cleaned_at=datetime.now()
                )
            )
            await session.commit()
            print(f"[RECEPTION] {room_number} xona holati Clean ga yangilandi")

    async def on_room_cleaning_started(data: dict):
        """
        Cleaning servis tozalashni boshlaganda xona holati Cleaning ga o'tadi.
        """
        room_number = data.get("room_number")
        if not room_number:
            return

        async with AsyncSessionLocal() as session:
            await session.execute(
                update(RoomModel)
                .where(RoomModel.room_number == room_number)
                .values(status=RoomStatus.CLEANING)
            )
            await session.commit()
            print(f"[RECEPTION] {room_number} xona holati Cleaning ga yangilandi")

    async def on_maintenance_request(data: dict):
        """
        Maintenance servis muammo yaratganda xona holati Maintenance ga o'tadi.
        """
        room_number = data.get("room_number")
        if not room_number:
            return

        async with AsyncSessionLocal() as session:
            await session.execute(
                update(RoomModel)
                .where(RoomModel.room_number == room_number)
                .values(status=RoomStatus.MAINTENANCE)
            )
            await session.commit()
            print(f"[RECEPTION] {room_number} xona holati Maintenance ga yangilandi")

    async def on_maintenance_completed(data: dict):
        """
        Maintenance servis muammo yakunlanganda xona yana Clean holatiga qaytadi.
        """
        room_number = data.get("room_number")
        if not room_number:
            return

        async with AsyncSessionLocal() as session:
            await session.execute(
                update(RoomModel)
                .where(RoomModel.room_number == room_number)
                .values(status=RoomStatus.CLEAN, cleaned_at=datetime.now())
            )
            await session.commit()
            print(f"[RECEPTION] {room_number} xona holati Clean ga qaytdi")

    broker.subscribe(Channels.ROOM_CLEANED, on_room_cleaned)
    broker.subscribe(Channels.ROOM_CLEANING_STARTED, on_room_cleaning_started)
    broker.subscribe(Channels.MAINTENANCE_REQUEST, on_maintenance_request)
    broker.subscribe(Channels.MAINTENANCE_COMPLETED, on_maintenance_completed)

    # Broker ishga tushirish
    broker.set_event_loop(asyncio.get_running_loop())
    broker.start()

    print("[RECEPTION] Servis tayyor")

    yield

    # Shutdown
    print("[RECEPTION] Servis to'xtatilmoqda...")


app = FastAPI(
    title="HotelOS — Reception Service",
    description="GrandStay mehmonxonasi qabulxona servisi",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api/reception", tags=["Reception"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "reception-service"}
