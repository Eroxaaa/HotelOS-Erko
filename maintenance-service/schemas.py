from pydantic import BaseModel, Field, field_validator
from typing import Optional
from models import IssueStatus, IssuePriority


class IssueCreateSchema(BaseModel):
    """
    Yangi texnik muammo yaratish uchun sxema.
    """
    room_number: str = Field(..., min_length=1, max_length=10, example="101")
    description: str = Field(..., min_length=5, max_length=255, example="Konditsioner ishlamayapti")
    priority: IssuePriority = Field(default=IssuePriority.NORMAL, example="normal")

    @field_validator("description")
    @classmethod
    def description_must_be_valid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Tavsif bo'sh bo'lmasligi kerak")
        return v.strip()


class IssueUpdateSchema(BaseModel):
    """
    Texnik muammo holatini yangilash uchun sxema.
    """
    status: IssueStatus = Field(..., example="completed")
    technician_id: Optional[str] = Field(default=None, example="T001")


class IssueResponseSchema(BaseModel):
    """
    Texnik muammo ma'lumotlarini qaytarish uchun sxema.
    """
    id: str
    room_number: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TechnicianResponseSchema(BaseModel):
    """
    Texnik xodim ma'lumotlarini qaytarish uchun sxema.
    """
    employee_id: str
    full_name: str
    shift: str
    specialization: Optional[str] = None
    is_available: bool
    resolved_count: int