from pydantic import BaseModel, Field, field_validator
from typing import Optional
from models import RoomType, RoomStatus, ProximityType


class RoomCreateSchema(BaseModel):
    """
    Yangi xona qo'shish uchun sxema.
    API ga kelgan ma'lumotlar shu model orqali tekshiriladi.
    """
    room_number: str = Field(..., min_length=1, max_length=10, example="101")
    room_type: RoomType = Field(..., example="single")
    floor: int = Field(..., ge=1, le=50, example=1)
    daily_rate: float = Field(..., gt=0, example=100.0)
    proximity: ProximityType = Field(default=ProximityType.NONE, example="elevator")

    @field_validator("room_number")
    @classmethod
    def room_number_must_be_valid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Xona raqami bo'sh bo'lmasligi kerak")
        return v.strip()


class CheckInSchema(BaseModel):
    """
    Mehmon check-in qilish uchun sxema.
    """
    guest_id: str = Field(..., min_length=1, example="G001")
    full_name: str = Field(..., min_length=2, max_length=100, example="Alisher Karimov")
    room_type: RoomType = Field(..., example="double")
    floor_preference: Optional[int] = Field(default=None, ge=1, le=50, example=3)
    proximity_preference: ProximityType = Field(
        default=ProximityType.NONE,
        example="elevator"
    )

    @field_validator("full_name")
    @classmethod
    def full_name_must_be_valid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Ism bo'sh bo'lmasligi kerak")
        return v.strip()


class CheckOutSchema(BaseModel):
    """
    Mehmon check-out qilish uchun sxema.
    """
    guest_id: str = Field(..., min_length=1, example="G001")
    discount_percent: float = Field(default=0.0, ge=0, le=100, example=10.0)


class RoomResponseSchema(BaseModel):
    """
    Xona ma'lumotlarini qaytarish uchun sxema.
    """
    room_number: str
    room_type: str
    floor: int
    daily_rate: float
    proximity: str
    status: str
    cleaned_at: str
    guest_id: Optional[str] = None

    class Config:
        from_attributes = True


class CheckInResponseSchema(BaseModel):
    """
    Check-in natijasini qaytarish uchun sxema.
    """
    success: bool
    message: str
    guest_id: str
    room_number: Optional[str] = None
    floor: Optional[int] = None
    daily_rate: Optional[float] = None


class CheckOutResponseSchema(BaseModel):
    """
    Check-out natijasini qaytarish uchun sxema.
    """
    success: bool
    message: str
    guest_id: str
    room_number: Optional[str] = None
    nights_stayed: Optional[int] = None
    room_service_total: Optional[float] = None
    additional_charges: Optional[float] = None
    discount_percent: Optional[float] = None
    total_amount: Optional[float] = None


class GuestResponseSchema(BaseModel):
    """
    Mehmon ma'lumotlarini qaytarish uchun sxema.
    """
    guest_id: str
    full_name: str
    room_type: str
    floor_preference: Optional[int] = None
    proximity_preference: str
    room_number: Optional[str] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    nights_stayed: int