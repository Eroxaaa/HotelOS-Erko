import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from redis_client import broker, Channels

from database import get_db
from models import (
    CleaningTaskModel, CleanerModel,
    CleaningStatus, CleaningPriority
)
from schemas import (
    CleaningTaskCreateSchema,
    CleaningTaskUpdateSchema,
    CleaningTaskResponseSchema,
    CleanerResponseSchema
)

router = APIRouter()


# -------------------------
# Tozalovchi tayinlash algoritmi
# -------------------------

async def assign_cleaner(session: AsyncSession) -> CleanerModel | None:
    """
    Bo'sh tozalovchini topish.
    Birinchi bo'sh tozalovchi tayinlanadi.
    """
    result = await session.execute(
        select(CleanerModel).where(CleanerModel.is_available == True)
    )
    cleaners = result.scalars().all()
    return cleaners[0] if cleaners else None


# -------------------------
# Tozalash vazifalari
# -------------------------

@router.post("/tasks", response_model=CleaningTaskResponseSchema)
async def create_task(
    data: CleaningTaskCreateSchema,
    session: AsyncSession = Depends(get_db)
):
    """
    Yangi tozalash vazifasi yaratish.
    Broker orqali ham, to'g'ridan-to'g'ri ham chaqirilishi mumkin.
    """

    # Xona uchun allaqachon aktiv vazifa bormi
    result = await session.execute(
        select(CleaningTaskModel).where(
            CleaningTaskModel.room_number == data.room_number,
            CleaningTaskModel.status != CleaningStatus.COMPLETED
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"{data.room_number} xona uchun allaqachon aktiv vazifa mavjud"
        )

    # Bo'sh tozalovchi topish
    cleaner = await assign_cleaner(session)

    task = CleaningTaskModel(
        id=str(uuid.uuid4()),
        room_number=data.room_number,
        priority=data.priority,
        status=CleaningStatus.PENDING if not cleaner else CleaningStatus.IN_PROGRESS,
        assigned_to=cleaner.employee_id if cleaner else None,
        created_at=datetime.now(),
        started_at=datetime.now() if cleaner else None
    )
    session.add(task)

    # Tozalovchini band qilish
    if cleaner:
        await session.execute(
            update(CleanerModel)
            .where(CleanerModel.employee_id == cleaner.employee_id)
            .values(is_available=False)
        )

    await session.commit()
    await session.refresh(task)

    if task.status == CleaningStatus.IN_PROGRESS:
        broker.publish(Channels.ROOM_CLEANING_STARTED, {
            "room_number": task.room_number,
            "assigned_to": task.assigned_to,
            "started_at": datetime.now().isoformat()
        })
        broker.publish(Channels.DASHBOARD_UPDATE, {
            "event": "cleaning_started",
            "room_number": task.room_number,
            "assigned_to": task.assigned_to,
            "started_at": datetime.now().isoformat()
        })

    return _task_to_response(task)


@router.get("/tasks", response_model=list[CleaningTaskResponseSchema])
async def get_all_tasks(session: AsyncSession = Depends(get_db)):
    """Barcha tozalash vazifalari"""
    result = await session.execute(select(CleaningTaskModel))
    tasks = result.scalars().all()
    return [_task_to_response(t) for t in tasks]


@router.get("/tasks/pending", response_model=list[CleaningTaskResponseSchema])
async def get_pending_tasks(session: AsyncSession = Depends(get_db)):
    """Navbatda kutayotgan vazifalar"""
    result = await session.execute(
        select(CleaningTaskModel).where(
            CleaningTaskModel.status == CleaningStatus.PENDING
        )
    )
    tasks = result.scalars().all()
    return [_task_to_response(t) for t in tasks]


@router.patch("/tasks/{task_id}", response_model=CleaningTaskResponseSchema)
async def update_task(
    task_id: str,
    data: CleaningTaskUpdateSchema,
    session: AsyncSession = Depends(get_db)
):
    """
    Tozalash vazifasi holatini yangilash.
    Completed bo'lsa broker orqali reception-service ga xabar yuboriladi.
    """
    from redis_client import broker, Channels

    result = await session.execute(
        select(CleaningTaskModel).where(CleaningTaskModel.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Vazifa topilmadi")

    # Holatni yangilash
    update_values = {"status": data.status}

    if data.status == CleaningStatus.IN_PROGRESS:
        update_values["started_at"] = datetime.now()
        if data.cleaner_id:
            update_values["assigned_to"] = data.cleaner_id

        broker.publish(Channels.ROOM_CLEANING_STARTED, {
            "room_number": task.room_number,
            "assigned_to": data.cleaner_id or task.assigned_to,
            "started_at": datetime.now().isoformat()
        })
        broker.publish(Channels.DASHBOARD_UPDATE, {
            "event": "cleaning_started",
            "room_number": task.room_number,
            "assigned_to": data.cleaner_id or task.assigned_to,
            "started_at": datetime.now().isoformat()
        })

    elif data.status == CleaningStatus.COMPLETED:
        update_values["completed_at"] = datetime.now()

        # Tozalovchini bo'shatish
        if task.assigned_to:
            await session.execute(
                update(CleanerModel)
                .where(CleanerModel.employee_id == task.assigned_to)
                .values(is_available=True)
            )

        # Broker orqali reception-service ga xabar yuborish
        broker.publish(Channels.ROOM_CLEANED, {
            "room_number": task.room_number,
            "cleaned_at": datetime.now().isoformat(),
            "cleaned_by": task.assigned_to
        })

        # Dashboard ga xabar yuborish
        broker.publish(Channels.DASHBOARD_UPDATE, {
            "event": "room_cleaned",
            "room_number": task.room_number,
            "cleaned_at": datetime.now().isoformat()
        })

    await session.execute(
        update(CleaningTaskModel)
        .where(CleaningTaskModel.id == task_id)
        .values(**update_values)
    )

    await session.commit()

    result = await session.execute(
        select(CleaningTaskModel).where(CleaningTaskModel.id == task_id)
    )
    updated_task = result.scalar_one()
    return _task_to_response(updated_task)


# -------------------------
# Tozalovchilar
# -------------------------

@router.get("/cleaners", response_model=list[CleanerResponseSchema])
async def get_all_cleaners(session: AsyncSession = Depends(get_db)):
    """Barcha tozalovchilar ro'yxati"""
    result = await session.execute(select(CleanerModel))
    cleaners = result.scalars().all()
    return [
        CleanerResponseSchema(
            employee_id=c.employee_id,
            full_name=c.full_name,
            shift=c.shift,
            is_available=c.is_available
        )
        for c in cleaners
    ]


@router.get("/cleaners/available", response_model=list[CleanerResponseSchema])
async def get_available_cleaners(session: AsyncSession = Depends(get_db)):
    """Bo'sh tozalovchilar"""
    result = await session.execute(
        select(CleanerModel).where(CleanerModel.is_available == True)
    )
    cleaners = result.scalars().all()
    return [
        CleanerResponseSchema(
            employee_id=c.employee_id,
            full_name=c.full_name,
            shift=c.shift,
            is_available=c.is_available
        )
        for c in cleaners
    ]


# -------------------------
# Yordamchi funksiya
# -------------------------

def _task_to_response(task: CleaningTaskModel) -> CleaningTaskResponseSchema:
    return CleaningTaskResponseSchema(
        id=task.id,
        room_number=task.room_number,
        status=task.status,
        priority=task.priority,
        assigned_to=task.assigned_to,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None
    )
