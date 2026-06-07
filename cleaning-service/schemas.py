from pydantic import BaseModel, Field, field_validator
from typing import Optional
from models import CleaningStatus, CleaningPriority


class CleaningTaskCreateSchema(BaseModel):
    """
    Yangi tozalash vazifasi yaratish uchun sxema.
    Asosan broker orqali reception-service dan keladi.
    """
    room_number: str = Field(..., min_length=1, max_length=10, example="101")
    priority: CleaningPriority = Field(
        default=CleaningPriority.NORMAL,
        example="normal"
    )

    @field_validator("room_number")
    @classmethod
    def room_number_must_be_valid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Xona raqami bo'sh bo'lmasligi kerak")
        return v.strip()


class CleaningTaskUpdateSchema(BaseModel):
    """
    Tozalash vazifasi holatini yangilash uchun sxema.
    """
    status: CleaningStatus = Field(..., example="completed")
    cleaner_id: Optional[str] = Field(default=None, example="C001")


class CleaningTaskResponseSchema(BaseModel):
    """
    Tozalash vazifasi ma'lumotlarini qaytarish uchun sxema.
    """
    id: str
    room_number: str
    status: str
    priority: str
    assigned_to: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class CleanerResponseSchema(BaseModel):
    """
    Tozalovchi xodim ma'lumotlarini qaytarish uchun sxema.
    """
    employee_id: str
    full_name: str
    shift: str
    is_available: bool