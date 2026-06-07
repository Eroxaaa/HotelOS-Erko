from enum import Enum
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Enum as SAEnum


class RoomType(str, Enum):
    """Xona turlari"""
    SINGLE = "single"
    DOUBLE = "double"
    SUITE = "suite"
    ACCESSIBLE = "accessible"


class RoomStatus(str, Enum):
    """Xona holatlari"""
    CLEAN = "clean"
    DIRTY = "dirty"
    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"
    OCCUPIED = "occupied"


class ProximityType(str, Enum):
    """Yaqinlik afzalligi"""
    ELEVATOR = "elevator"
    STAIRS = "stairs"
    NONE = "none"


class Base(DeclarativeBase):
    pass

class RoomModel(Base):
    
    __tablename__ = "rooms"

    room_number: Mapped[str] = mapped_column(String(10), primary_key=True)
    room_type: Mapped[str] = mapped_column(SAEnum(RoomType), nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_rate: Mapped[float] = mapped_column(Float, nullable=False)
    proximity: Mapped[str] = mapped_column(
        SAEnum(ProximityType),
        default=ProximityType.NONE,
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        SAEnum(RoomStatus),
        default=RoomStatus.CLEAN,
        nullable=False
    )
    cleaned_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False
    )
    guest_id: Mapped[str] = mapped_column(String(50), nullable=True)

class GuestModel(Base):
    """
    Mehmon jadval modeli.
    PostgreSQL da guests jadvaliga mos keladi.
    """
    __tablename__ = "guests"

    guest_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    room_type: Mapped[str] = mapped_column(SAEnum(RoomType), nullable=False)
    floor_preference: Mapped[int] = mapped_column(Integer, nullable=True)
    proximity_preference: Mapped[str] = mapped_column(
        SAEnum(ProximityType),
        default=ProximityType.NONE,
        nullable=False
    )
    room_number: Mapped[str] = mapped_column(String(10), nullable=True)
    check_in_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    check_out_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_checked_out: Mapped[bool] = mapped_column(Boolean, default=False)