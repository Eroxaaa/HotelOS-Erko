from enum import Enum
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum


class IssueStatus(str, Enum):
    """Texnik muammo holatlari"""
    PENDING = "pending"           # Navbatda kutmoqda
    IN_PROGRESS = "in_progress"   # Hal qilinmoqda
    COMPLETED = "completed"       # Hal qilindi


class IssuePriority(str, Enum):
    """
    Texnik muammo ustuvorligi.
    Raqam kichik = ustuvorlik yuqori.
    """
    CRITICAL = "critical"   # 1 — Lift, elektr, suv
    HIGH = "high"           # 2 — Konditsioner, isitish
    NORMAL = "normal"       # 3 — Oddiy nosozlik
    LOW = "low"             # 4 — Shoshilinch emas


class Base(DeclarativeBase):
    pass


class IssueModel(Base):
    """
    Texnik muammo jadval modeli.
    PostgreSQL da issues jadvaliga mos keladi.
    """
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    room_number: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[str] = mapped_column(
        SAEnum(IssuePriority),
        default=IssuePriority.NORMAL,
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        SAEnum(IssueStatus),
        default=IssueStatus.PENDING,
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


class TechnicianModel(Base):
    """
    Texnik xodim jadval modeli.
    PostgreSQL da technicians jadvaliga mos keladi.
    """
    __tablename__ = "technicians"

    employee_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    shift: Mapped[str] = mapped_column(String(20), nullable=False)
    specialization: Mapped[str] = mapped_column(String(100), nullable=True)
    is_available: Mapped[bool] = mapped_column(default=True)
    resolved_count: Mapped[int] = mapped_column(Integer, default=0)