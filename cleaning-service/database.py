import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://cleaning_user:cleaning_pass@localhost:5434/cleaning_db"
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
    print("[DATABASE] Cleaning jadvallar yaratildi")


async def seed_db(session: AsyncSession) -> None:
    from sqlalchemy import select
    from models import CleanerModel

    result = await session.execute(select(CleanerModel))
    existing = result.scalars().all()

    if existing:
        print("[DATABASE] Cleaners allaqachon mavjud, seed o'tkazib yuborildi")
        return

    cleaners_data = [
        ("C001", "Nilufar Hasanova", "morning"),
        ("C002", "Sherzod Qodirov", "morning"),
        ("C003", "Malika Ergasheva", "evening"),
    ]

    for emp_id, full_name, shift in cleaners_data:
        cleaner = CleanerModel(
            employee_id=emp_id,
            full_name=full_name,
            shift=shift,
            is_available=True
        )
        session.add(cleaner)

    await session.commit()
    print(f"[DATABASE] {len(cleaners_data)} ta tozalovchi yuklandi")    