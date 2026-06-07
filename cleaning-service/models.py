import os
from enum import Enum
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Enum as SAEnum


class CleaningStatus(str, Enum):
    """Tozalash holatlari"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class CleaningPriority(str, Enum):
    """Tozalash ustuvorligi"""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class Base(DeclarativeBase):
    pass


class CleaningTaskModel(Base):
    """
    Tozalash vazifasi jadval modeli.
    PostgreSQL da cleaning_tasks jadvaliga mos keladi.
    """
    __tablename__ = "cleaning_tasks"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    room_number: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum(CleaningStatus),
        default=CleaningStatus.PENDING,
        nullable=False
    )
    priority: Mapped[str] = mapped_column(
        SAEnum(CleaningPriority),
        default=CleaningPriority.NORMAL,
        nullable=False
    )
    assigned_to: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class CleanerModel(Base):
    """
    Tozalovchi xodim jadval modeli.
    PostgreSQL da cleaners jadvaliga mos keladi.
    """
    __tablename__ = "cleaners"

    employee_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    shift: Mapped[str] = mapped_column(String(20), nullable=False)
    is_available: Mapped[bool] = mapped_column(default=True)