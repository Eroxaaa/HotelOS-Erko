from enum import Enum
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, Enum as SAEnum


class OrderStatus(str, Enum):
    """Buyurtma holatlari"""
    PENDING = "pending"         # Qabul qilindi
    PREPARING = "preparing"     # Tayyorlanmoqda
    DELIVERED = "delivered"     # Yetkazildi
    CANCELLED = "cancelled"     # Bekor qilindi


class OrderCategory(str, Enum):
    """Buyurtma kategoriyalari"""
    FOOD = "food"               # Ovqat
    BEVERAGE = "beverage"       # Ichimlik
    HOUSEKEEPING = "housekeeping"  # Uy-ro'zg'or
    OTHER = "other"             # Boshqa


class Base(DeclarativeBase):
    pass


class OrderModel(Base):
    """
    Xona xizmati buyurtmasi jadval modeli.
    PostgreSQL da orders jadvaliga mos keladi.
    """
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    room_number: Mapped[str] = mapped_column(String(10), nullable=False)
    guest_id: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(SAEnum(OrderCategory), nullable=False)
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum(OrderStatus),
        default=OrderStatus.PENDING,
        nullable=False
    )
    notes: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False
    )
    delivered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class MenuItemModel(Base):
    """
    Menyu elementi jadval modeli.
    PostgreSQL da menu_items jadvaliga mos keladi.
    """
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(SAEnum(OrderCategory), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    is_available: Mapped[bool] = mapped_column(default=True)