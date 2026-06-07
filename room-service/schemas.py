from pydantic import BaseModel, Field, field_validator
from typing import Optional
from models import OrderStatus, OrderCategory


class OrderCreateSchema(BaseModel):
    """
    Yangi buyurtma yaratish uchun sxema.
    """
    room_number: str = Field(..., min_length=1, max_length=10, example="101")
    guest_id: str = Field(..., min_length=1, example="G001")
    category: OrderCategory = Field(..., example="food")
    item_name: str = Field(..., min_length=1, max_length=100, example="Osh")
    quantity: int = Field(default=1, ge=1, le=10, example=2)
    unit_price: float = Field(..., gt=0, example=15.0)
    notes: Optional[str] = Field(default=None, max_length=255, example="Achchiq bo'lmasin")

    @field_validator("item_name")
    @classmethod
    def item_name_must_be_valid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Buyurtma nomi bo'sh bo'lmasligi kerak")
        return v.strip()


class OrderUpdateSchema(BaseModel):
    """
    Buyurtma holatini yangilash uchun sxema.
    """
    status: OrderStatus = Field(..., example="delivered")


class OrderResponseSchema(BaseModel):
    """
    Buyurtma ma'lumotlarini qaytarish uchun sxema.
    """
    id: str
    room_number: str
    guest_id: str
    category: str
    item_name: str
    quantity: int
    unit_price: float
    total_price: float
    status: str
    notes: Optional[str] = None
    created_at: str
    delivered_at: Optional[str] = None


class MenuItemResponseSchema(BaseModel):
    """
    Menyu elementi ma'lumotlarini qaytarish uchun sxema.
    """
    id: str
    name: str
    category: str
    price: float
    is_available: bool