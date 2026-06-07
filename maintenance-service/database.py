import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models import Base, TechnicianModel

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://maintenance_user:maintenance_pass@localhost:5436/maintenance_db"
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
    print("[DATABASE] Maintenance jadvallar yaratildi")


async def seed_db(session: AsyncSession) -> None:
    from sqlalchemy import select

    result = await session.execute(select(TechnicianModel))
    existing = result.scalars().all()

    if existing:
        print("[DATABASE] Texniklar allaqachon mavjud, seed o'tkazib yuborildi")
        return

    technicians_data = [
        ("T001", "Bobur Mirzayev", "morning", "Elektr va suv"),
        ("T002", "Sanjar Holiqov", "morning", "Konditsioner va isitish"),
        ("T003", "Ulugbek Nazarov", "evening", "Umumiy nosozliklar"),
    ]

    for emp_id, full_name, shift, specialization in technicians_data:
        technician = TechnicianModel(
            employee_id=emp_id,
            full_name=full_name,
            shift=shift,
            specialization=specialization,
            is_available=True,
            resolved_count=0
        )
        session.add(technician)

    await session.commit()
    print(f"[DATABASE] {len(technicians_data)} ta texnik yuklandi")