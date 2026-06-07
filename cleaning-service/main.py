# Cleaning Service v1.0

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from database import init_db, seed_db, AsyncSessionLocal
from redis_client import broker, Channels
    

async def on_room_vacated(data: dict) -> None:
    """
    Reception-service dan "xona bo'shatildi" xabari kelganda
    avtomatik tozalash vazifasi yaratiladi.
    """
    room_number = data.get("room_number")
    if not room_number:
        return

    print(f"[CLEANING] {room_number} xona bo'shatildi, tozalash vazifasi yaratilmoqda...")

    async with AsyncSessionLocal() as session:
        from models import CleaningTaskModel, CleanerModel, CleaningStatus
        from sqlalchemy import select, update
        from sqlalchemy.exc import IntegrityError
        import uuid
        from datetime import datetime

        # Allaqachon aktiv vazifa bormi
        result = await session.execute(
            select(CleaningTaskModel).where(
                CleaningTaskModel.room_number == room_number,
                CleaningTaskModel.status != CleaningStatus.COMPLETED
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"[CLEANING] {room_number} uchun allaqachon vazifa mavjud")
            return

        # Bo'sh tozalovchi topish
        result = await session.execute(
            select(CleanerModel).where(CleanerModel.is_available == True)
        )
        cleaners = result.scalars().all()
        cleaner = cleaners[0] if cleaners else None

        # Vazifa yaratish
        task = CleaningTaskModel(
            id=str(uuid.uuid4()),
            room_number=room_number,
            status=CleaningStatus.IN_PROGRESS if cleaner else CleaningStatus.PENDING,
            assigned_to=cleaner.employee_id if cleaner else None,
            created_at=datetime.now(),
            started_at=datetime.now() if cleaner else None
        )
        session.add(task)

        # Tozalovchini band qilish
        if cleaner:
            await session.execute(
                update(CleanerModel)
                .where(CleanerModel.employee_id == cleaner.employee_id)
                .values(is_available=False)
            )

        await session.commit()

        if cleaner:
            broker.publish(Channels.ROOM_CLEANING_STARTED, {
                "room_number": room_number,
                "assigned_to": cleaner.employee_id,
                "started_at": datetime.now().isoformat()
            })

        # Dashboard ga xabar yuborish
        broker.publish(Channels.DASHBOARD_UPDATE, {
            "event": "cleaning_started",
            "room_number": room_number,
            "assigned_to": cleaner.employee_id if cleaner else None,
            "started_at": datetime.now().isoformat()
        })

        print(f"[CLEANING] {room_number} tozalash vazifasi yaratildi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI ishga tushganda va to'xtaganda bajariladigan amallar.
    """

    print("[CLEANING] Servis ishga tushmoqda...")

    # Jadvallar yaratish
    await init_db()

    # Namuna ma'lumotlar yuklash
    async with AsyncSessionLocal() as session:
        await seed_db(session)

    # Reception-service dan xabarlarni tinglash
    broker.subscribe(Channels.ROOM_VACATED, on_room_vacated)

    # Broker ishga tushirish
    broker.set_event_loop(asyncio.get_running_loop())
    broker.start()

    print("[CLEANING] Servis tayyor")

    yield

    print("[CLEANING] Servis to'xtatilmoqda...")


app = FastAPI(
    title="HotelOS — Cleaning Service",
    description="GrandStay mehmonxonasi tozalash servisi",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api/cleaning", tags=["Cleaning"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "cleaning-service"}
