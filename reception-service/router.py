from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from typing import Optional

from database import get_db
from models import RoomModel, GuestModel, RoomStatus, ProximityType, RoomType
from schemas import (
    CheckInSchema,
    CheckOutSchema,
    RoomCreateSchema,
    CheckInResponseSchema,
    CheckOutResponseSchema,
    RoomResponseSchema
)

router = APIRouter()


# -------------------------
# Xona tayinlash algoritmi
# -------------------------

async def assign_room(
    session: AsyncSession,
    room_type: RoomType,
    floor_preference: Optional[int],
    proximity_preference: ProximityType
) -> Optional[RoomModel]:
    """
    Xona tayinlash algoritmi — P1 da tasvirlangan
    blok-sxemaning Python kod ko'rinishi.
    """

    # 1. Filtr: faqat Clean xonalar — WITH FOR UPDATE qulflash bilan
    
    result = await session.execute(
        select(RoomModel)
        .where(RoomModel.status == RoomStatus.CLEAN)
        .with_for_update()
    )
    clean_rooms = result.scalars().all()

    if not clean_rooms:
        return None

    # 2. Filtr: faqat so'ralgan tur
    typed_rooms = [r for r in clean_rooms if r.room_type == room_type]

    if not typed_rooms:
        return None

    # 3. Saralash: eng uzoq vaqt toza turgan birinchi
    sorted_rooms = sorted(typed_rooms, key=lambda r: r.cleaned_at)

    # 4. Qavat afzalligi
    if floor_preference is not None:
        preferred = [r for r in sorted_rooms if r.floor == floor_preference]
        others = [r for r in sorted_rooms if r.floor != floor_preference]
        sorted_rooms = preferred + others

    # 5. Yaqinlik afzalligi
    if proximity_preference != ProximityType.NONE:
        preferred = [r for r in sorted_rooms if r.proximity == proximity_preference]
        others = [r for r in sorted_rooms if r.proximity != proximity_preference]
        sorted_rooms = preferred + others

    return sorted_rooms[0] if sorted_rooms else None


# -------------------------
# Hisob-kitob algoritmi
# -------------------------

async def calculate_bill(
    session: AsyncSession,
    guest: GuestModel,
    discount_percent: float
) -> dict:
    """
    Check-out da to'lov summasini hisoblash algoritmi.
    """

    # Tunlar soni
    check_in = guest.check_in_time
    check_out = datetime.now()
    delta = check_out - check_in
    nights = delta.days if delta.days > 0 else 1

    # Xona kunlik narxi
    result = await session.execute(
        select(RoomModel).where(RoomModel.room_number == guest.room_number)
    )
    room = result.scalar_one_or_none()
    daily_rate = room.daily_rate if room else 0.0

    # Asosiy summa
    base_amount = daily_rate * nights

    # Chegirma
    if 0 < discount_percent <= 100:
        discount_amount = base_amount * (discount_percent / 100)
    else:
        discount_amount = 0.0

    total = base_amount - discount_amount

    return {
        "nights": nights,
        "daily_rate": daily_rate,
        "base_amount": base_amount,
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "total": round(total, 2)
    }


# -------------------------
# Xona endpointlari
# -------------------------

@router.post("/rooms", response_model=RoomResponseSchema)
async def create_room(
    data: RoomCreateSchema,
    session: AsyncSession = Depends(get_db)
):
    """Yangi xona qo'shish"""

    # Xona allaqachon mavjudmi
    result = await session.execute(
        select(RoomModel).where(RoomModel.room_number == data.room_number)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Bu raqamli xona allaqachon mavjud")

    room = RoomModel(
        room_number=data.room_number,
        room_type=data.room_type,
        floor=data.floor,
        daily_rate=data.daily_rate,
        proximity=data.proximity,
        status=RoomStatus.CLEAN,
        cleaned_at=datetime.now()
    )
    session.add(room)
    await session.commit()
    await session.refresh(room)

    return RoomResponseSchema(
        room_number=room.room_number,
        room_type=room.room_type,
        floor=room.floor,
        daily_rate=room.daily_rate,
        proximity=room.proximity,
        status=room.status,
        cleaned_at=room.cleaned_at.isoformat(),
        guest_id=room.guest_id
    )


@router.get("/rooms", response_model=list[RoomResponseSchema])
async def get_all_rooms(session: AsyncSession = Depends(get_db)):
    """Barcha xonalar ro'yxati"""
    result = await session.execute(select(RoomModel))
    rooms = result.scalars().all()
    return [
        RoomResponseSchema(
            room_number=r.room_number,
            room_type=r.room_type,
            floor=r.floor,
            daily_rate=r.daily_rate,
            proximity=r.proximity,
            status=r.status,
            cleaned_at=r.cleaned_at.isoformat(),
            guest_id=r.guest_id
        )
        for r in rooms
    ]


@router.get("/rooms/{room_number}", response_model=RoomResponseSchema)
async def get_room(room_number: str, session: AsyncSession = Depends(get_db)):
    """Bitta xona ma'lumoti"""
    result = await session.execute(
        select(RoomModel).where(RoomModel.room_number == room_number)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(
            status_code=404, 
            detail="Xona topilmadi"
        )

    return RoomResponseSchema(
        room_number=room.room_number,
        room_type=room.room_type,
        floor=room.floor,
        daily_rate=room.daily_rate,
        proximity=room.proximity,
        status=room.status,
        cleaned_at=room.cleaned_at.isoformat(),
        guest_id=room.guest_id
    )


# -------------------------
# Check-in / Check-out
# -------------------------

@router.post("/checkin", response_model=CheckInResponseSchema)
async def check_in(
    data: CheckInSchema,
    session: AsyncSession = Depends(get_db)
):
    """
    Mehmon check-in qilish.
    Xona tayinlash algoritmi ishga tushadi.
    """

    # Mehmon allaqachon check-in qilganmi
    result = await session.execute(
        select(GuestModel).where(
            GuestModel.guest_id == data.guest_id,
            GuestModel.is_checked_out == False
        )
    )
    existing_guest = result.scalar_one_or_none()
    if existing_guest:
        raise HTTPException(status_code=400, detail="Bu mehmon allaqachon check-in qilgan")

    # Xona tayinlash algoritmi
    room = await assign_room(
        session=session,
        room_type=data.room_type,
        floor_preference=data.floor_preference,
        proximity_preference=data.proximity_preference
    )

    if not room:
        raise HTTPException(
            status_code=404,
            detail=f"'{data.room_type}' turidagi bo'sh xona topilmadi"
        )

    # Mehmonni saqlash
    guest = GuestModel(
        guest_id=data.guest_id,
        full_name=data.full_name,
        room_type=data.room_type,
        floor_preference=data.floor_preference,
        proximity_preference=data.proximity_preference,
        room_number=room.room_number,
        check_in_time=datetime.now(),
        is_checked_out=False
    )
    session.add(guest)

    # Xona holatini yangilash
    await session.execute(
        update(RoomModel)
        .where(RoomModel.room_number == room.room_number)
        .values(status=RoomStatus.OCCUPIED, guest_id=data.guest_id)
    )

    await session.commit()

    from redis_client import broker, Channels

    broker.publish(Channels.DASHBOARD_UPDATE, {
        "event": "checkin",
        "guest_id": data.guest_id,
        "guest_name": data.full_name,
        "room_number": room.room_number,
        "room_type": data.room_type,
        "checked_in_at": datetime.now().isoformat()
    })

    return CheckInResponseSchema(
        success=True,
        message=f"{data.full_name} muvaffaqiyatli check-in qildi",
        guest_id=data.guest_id,
        room_number=room.room_number,
        floor=room.floor,
        daily_rate=room.daily_rate
    )


@router.post("/checkout", response_model=CheckOutResponseSchema)
async def check_out(
    data: CheckOutSchema,
    session: AsyncSession = Depends(get_db)
):
    """
    Mehmon check-out qilish.
    Hisob-kitob algoritmi ishga tushadi.
    Broker orqali cleaning-service ga xabar yuboriladi.
    """
    from redis_client import broker, Channels

    # Mehmon mavjudmi
    result = await session.execute(
        select(GuestModel).where(
            GuestModel.guest_id == data.guest_id,
            GuestModel.is_checked_out == False
        )
    )
    guest = result.scalar_one_or_none()
    if not guest:
        raise HTTPException(status_code=404, detail="Mehmon topilmadi")

    # Hisob-kitob
    bill = await calculate_bill(
        session=session,
        guest=guest,
        discount_percent=data.discount_percent
    )

    room_number = guest.room_number

    # Mehmonni check-out qilish
    await session.execute(
        update(GuestModel)
        .where(GuestModel.guest_id == data.guest_id)
        .values(
            check_out_time=datetime.now(),
            is_checked_out=True
        )
    )

    # Xona holatini Dirty ga o'zgartirish
    await session.execute(
        update(RoomModel)
        .where(RoomModel.room_number == room_number)
        .values(status=RoomStatus.DIRTY, guest_id=None)
    )

    await session.commit()

    broker.publish(Channels.DASHBOARD_UPDATE, {
        "event": "checkout",
        "guest_id": data.guest_id,
        "room_number": room_number,
        "checked_out_at": datetime.now().isoformat()
    })

    # Broker orqali cleaning-service ga xabar yuborish
    broker.publish(Channels.ROOM_VACATED, {
        "room_number": room_number,
        "vacated_at": datetime.now().isoformat()
    })

    return CheckOutResponseSchema(
        success=True,
        message=f"Mehmon muvaffaqiyatli check-out qildi",
        guest_id=data.guest_id,
        room_number=room_number,
        nights_stayed=bill["nights"],
        room_service_total=0.0,
        additional_charges=0.0,
        discount_percent=bill["discount_percent"],
        total_amount=bill["total"]
    )


@router.get("/guests", response_model=list)
async def get_all_guests(session: AsyncSession = Depends(get_db)):
    """Barcha aktiv mehmonlar ro'yxati"""
    result = await session.execute(
        select(GuestModel).where(GuestModel.is_checked_out == False)
    )
    guests = result.scalars().all()
    return [
        {
            "guest_id": g.guest_id,
            "full_name": g.full_name,
            "room_number": g.room_number,
            "room_type": g.room_type,
            "check_in_time": g.check_in_time.isoformat() if g.check_in_time else None
        }
        for g in guests
    ]


@router.get("/guests/{guest_id}")
async def get_guest(guest_id: str, session: AsyncSession = Depends(get_db)):
    """Bitta mehmon ma'lumoti"""
    result = await session.execute(
        select(GuestModel).where(GuestModel.guest_id == guest_id)
    )
    guest = result.scalar_one_or_none()
    if not guest:
        raise HTTPException(status_code=404, detail="Mehmon topilmadi")

    return {
        "guest_id": guest.guest_id,
        "full_name": guest.full_name,
        "room_number": guest.room_number,
        "room_type": guest.room_type,
        "floor_preference": guest.floor_preference,
        "proximity_preference": guest.proximity_preference,
        "check_in_time": guest.check_in_time.isoformat() if guest.check_in_time else None,
        "check_out_time": guest.check_out_time.isoformat() if guest.check_out_time else None,
        "is_checked_out": guest.is_checked_out
    }
