import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models import Base, RoomModel, RoomStatus, RoomType, ProximityType
from datetime import datetime

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://reception_user:reception_pass@localhost:5433/reception_db"
)

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[DATABASE] Reception jadvallar yaratildi")


async def seed_db(session: AsyncSession) -> None:
    from sqlalchemy import select

    result = await session.execute(select(RoomModel))
    existing = result.scalars().all()

    if existing:
        print("[DATABASE] Xonalar allaqachon mavjud, seed o'tkazib yuborildi")
        return

    rooms_data = [
        # 1-qavat
        ("101", RoomType.SINGLE, 1, 80.0, ProximityType.STAIRS),
        ("102", RoomType.SINGLE, 1, 80.0, ProximityType.ELEVATOR),
        ("103", RoomType.DOUBLE, 1, 120.0, ProximityType.STAIRS),
        ("104", RoomType.ACCESSIBLE, 1, 100.0, ProximityType.ELEVATOR),
        # 2-qavat
        ("201", RoomType.SINGLE, 2, 85.0, ProximityType.STAIRS),
        ("202", RoomType.DOUBLE, 2, 125.0, ProximityType.ELEVATOR),
        ("203", RoomType.SUITE, 2, 200.0, ProximityType.ELEVATOR),
        ("204", RoomType.SINGLE, 2, 85.0, ProximityType.NONE),
        # 3-qavat
        ("301", RoomType.DOUBLE, 3, 130.0, ProximityType.STAIRS),
        ("302", RoomType.SUITE, 3, 210.0, ProximityType.ELEVATOR),
        ("303", RoomType.SINGLE, 3, 90.0, ProximityType.NONE),
        ("304", RoomType.ACCESSIBLE, 3, 105.0, ProximityType.ELEVATOR),
    ]

    for room_number, room_type, floor, daily_rate, proximity in rooms_data:
        room = RoomModel(
            room_number=room_number,
            room_type=room_type,
            floor=floor,
            daily_rate=daily_rate,
            proximity=proximity,
            status=RoomStatus.CLEAN,
            cleaned_at=datetime.now()
        )
        session.add(room)

    await session.commit()
    print(f"[DATABASE] {len(rooms_data)} ta xona yuklandi")