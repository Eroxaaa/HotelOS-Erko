import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models import Base, MenuItemModel, OrderCategory

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://room_user:room_pass@localhost:5435/room_db"
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
    print("[DATABASE] Room-service jadvallar yaratildi")


async def seed_db(session: AsyncSession) -> None:
    from sqlalchemy import select
    import uuid

    result = await session.execute(select(MenuItemModel))
    existing = result.scalars().all()

    if existing:
        print("[DATABASE] Menyu allaqachon mavjud, seed o'tkazib yuborildi")
        return

    menu_data = [
        # Ovqatlar
        ("Osh", OrderCategory.FOOD, 15.0),
        ("Lag'mon", OrderCategory.FOOD, 12.0),
        ("Manti", OrderCategory.FOOD, 10.0),
        ("Tovuq kabob", OrderCategory.FOOD, 18.0),
        ("Salat", OrderCategory.FOOD, 7.0),
        # Ichimliklar
        ("Choy", OrderCategory.BEVERAGE, 3.0),
        ("Qahva", OrderCategory.BEVERAGE, 5.0),
        ("Meva sharbati", OrderCategory.BEVERAGE, 6.0),
        ("Mineral suv", OrderCategory.BEVERAGE, 2.0),
        # Uy-ro'zg'or
        ("Qo'shimcha sochiq", OrderCategory.HOUSEKEEPING, 0.0),
        ("Yostiq", OrderCategory.HOUSEKEEPING, 0.0),
        ("Shampun", OrderCategory.HOUSEKEEPING, 2.0),
    ]

    for name, category, price in menu_data:
        item = MenuItemModel(
            id=str(uuid.uuid4()),
            name=name,
            category=category,
            price=price,
            is_available=True
        )
        session.add(item)

    await session.commit()
    print(f"[DATABASE] {len(menu_data)} ta menyu elementi yuklandi")