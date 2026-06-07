import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from database import get_db
from models import (
    IssueModel, TechnicianModel,
    IssueStatus, IssuePriority
)
from schemas import (
    IssueCreateSchema,
    IssueUpdateSchema,
    IssueResponseSchema,
    TechnicianResponseSchema
)

router = APIRouter()

# Ustuvorlik tartibi — kichik raqam = yuqori ustuvorlik
PRIORITY_ORDER = {
    IssuePriority.CRITICAL: 1,
    IssuePriority.HIGH: 2,
    IssuePriority.NORMAL: 3,
    IssuePriority.LOW: 4
}


# -------------------------
# Texnik tayinlash algoritmi
# -------------------------

async def assign_technician(session: AsyncSession) -> TechnicianModel | None:
    """
    Bo'sh texnikni topish.
    Birinchi bo'sh texnik tayinlanadi.
    """
    result = await session.execute(
        select(TechnicianModel).where(TechnicianModel.is_available == True)
    )
    technicians = result.scalars().all()
    return technicians[0] if technicians else None


# -------------------------
# Texnik muammolar
# -------------------------

@router.post("/issues", response_model=IssueResponseSchema)
async def create_issue(
    data: IssueCreateSchema,
    session: AsyncSession = Depends(get_db)
):
    """
    Yangi texnik muammo yaratish.
    Texnik tayinlash algoritmi ishga tushadi.
    """
    from redis_client import broker, Channels

    # Bo'sh texnik topish
    technician = await assign_technician(session)

    issue = IssueModel(
        id=str(uuid.uuid4()),
        room_number=data.room_number,
        description=data.description,
        priority=data.priority,
        status=IssueStatus.IN_PROGRESS if technician else IssueStatus.PENDING,
        assigned_to=technician.employee_id if technician else None,
        created_at=datetime.now(),
        started_at=datetime.now() if technician else None
    )
    session.add(issue)

    # Texnikni band qilish
    if technician:
        await session.execute(
            update(TechnicianModel)
            .where(TechnicianModel.employee_id == technician.employee_id)
            .values(is_available=False)
        )

    await session.commit()
    await session.refresh(issue)

    broker.publish(Channels.MAINTENANCE_REQUEST, {
        "room_number": data.room_number,
        "description": data.description,
        "priority": data.priority,
        "issue_id": issue.id,
        "created_at": datetime.now().isoformat()
    })

    # Dashboard ga xabar yuborish
    broker.publish(Channels.DASHBOARD_UPDATE, {
        "event": "maintenance_request",
        "room_number": data.room_number,
        "description": data.description,
        "priority": data.priority,
        "assigned_to": technician.employee_id if technician else None,
        "created_at": datetime.now().isoformat()
    })

    return _issue_to_response(issue)


@router.get("/issues", response_model=list[IssueResponseSchema])
async def get_all_issues(session: AsyncSession = Depends(get_db)):
    """Barcha texnik muammolar — ustuvorlik bo'yicha saralangan"""
    result = await session.execute(select(IssueModel))
    issues = result.scalars().all()

    # Ustuvorlik bo'yicha saralash
    sorted_issues = sorted(
        issues,
        key=lambda i: (PRIORITY_ORDER.get(i.priority, 99), i.created_at)
    )
    return [_issue_to_response(i) for i in sorted_issues]


@router.get("/issues/pending", response_model=list[IssueResponseSchema])
async def get_pending_issues(session: AsyncSession = Depends(get_db)):
    """Navbatda kutayotgan muammolar"""
    result = await session.execute(
        select(IssueModel).where(IssueModel.status == IssueStatus.PENDING)
    )
    issues = result.scalars().all()
    sorted_issues = sorted(
        issues,
        key=lambda i: (PRIORITY_ORDER.get(i.priority, 99), i.created_at)
    )
    return [_issue_to_response(i) for i in sorted_issues]


@router.get("/issues/{issue_id}", response_model=IssueResponseSchema)
async def get_issue(issue_id: str, session: AsyncSession = Depends(get_db)):
    """Bitta texnik muammo ma'lumoti"""
    result = await session.execute(
        select(IssueModel).where(IssueModel.id == issue_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Muammo topilmadi")
    return _issue_to_response(issue)


@router.patch("/issues/{issue_id}", response_model=IssueResponseSchema)
async def update_issue(
    issue_id: str,
    data: IssueUpdateSchema,
    session: AsyncSession = Depends(get_db)
):
    """
    Texnik muammo holatini yangilash.
    Completed bo'lsa texnik bo'shatiladi va
    navbatdagi muammoga tayinlanadi.
    """
    from redis_client import broker, Channels

    result = await session.execute(
        select(IssueModel).where(IssueModel.id == issue_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Muammo topilmadi")

    update_values = {"status": data.status}

    if data.status == IssueStatus.IN_PROGRESS:
        update_values["started_at"] = datetime.now()
        if data.technician_id:
            update_values["assigned_to"] = data.technician_id

    elif data.status == IssueStatus.COMPLETED:
        update_values["completed_at"] = datetime.now()

        # Texnikni bo'shatish va resolved_count oshirish
        if issue.assigned_to:
            await session.execute(
                update(TechnicianModel)
                .where(TechnicianModel.employee_id == issue.assigned_to)
                .values(
                    is_available=True,
                    resolved_count=TechnicianModel.resolved_count + 1
                )
            )

        # Dashboard ga xabar yuborish
        broker.publish(Channels.DASHBOARD_UPDATE, {
            "event": "maintenance_completed",
            "issue_id": issue_id,
            "room_number": issue.room_number,
            "completed_at": datetime.now().isoformat()
        })

        broker.publish(Channels.MAINTENANCE_COMPLETED, {
            "issue_id": issue_id,
            "room_number": issue.room_number,
            "completed_at": datetime.now().isoformat()
        })

        # Navbatdagi pending muammoni tekshirish va tayinlash
        pending_result = await session.execute(
            select(IssueModel)
            .where(IssueModel.status == IssueStatus.PENDING)
            .order_by(IssueModel.created_at)
        )
        pending_issues = pending_result.scalars().all()

        if pending_issues:
            sorted_pending = sorted(
                pending_issues,
                key=lambda i: (PRIORITY_ORDER.get(i.priority, 99), i.created_at)
            )
            next_issue = sorted_pending[0]

            # Bo'shagan texnikni navbatdagi muammoga tayinlash
            await session.execute(
                update(IssueModel)
                .where(IssueModel.id == next_issue.id)
                .values(
                    status=IssueStatus.IN_PROGRESS,
                    assigned_to=issue.assigned_to,
                    started_at=datetime.now()
                )
            )
            await session.execute(
                update(TechnicianModel)
                .where(TechnicianModel.employee_id == issue.assigned_to)
                .values(is_available=False)
            )

            broker.publish(Channels.DASHBOARD_UPDATE, {
                "event": "maintenance_assigned",
                "issue_id": next_issue.id,
                "room_number": next_issue.room_number,
                "assigned_to": issue.assigned_to,
                "started_at": datetime.now().isoformat()
            })

    await session.execute(
        update(IssueModel)
        .where(IssueModel.id == issue_id)
        .values(**update_values)
    )
    await session.commit()

    result = await session.execute(
        select(IssueModel).where(IssueModel.id == issue_id)
    )
    updated_issue = result.scalar_one()
    return _issue_to_response(updated_issue)


# -------------------------
# Texniklar
# -------------------------

@router.get("/technicians", response_model=list[TechnicianResponseSchema])
async def get_all_technicians(session: AsyncSession = Depends(get_db)):
    """Barcha texniklar ro'yxati"""
    result = await session.execute(select(TechnicianModel))
    technicians = result.scalars().all()
    return [_technician_to_response(t) for t in technicians]


@router.get("/technicians/available", response_model=list[TechnicianResponseSchema])
async def get_available_technicians(session: AsyncSession = Depends(get_db)):
    """Bo'sh texniklar"""
    result = await session.execute(
        select(TechnicianModel).where(TechnicianModel.is_available == True)
    )
    technicians = result.scalars().all()
    return [_technician_to_response(t) for t in technicians]


# -------------------------
# Yordamchi funksiyalar
# -------------------------

def _issue_to_response(issue: IssueModel) -> IssueResponseSchema:
    return IssueResponseSchema(
        id=issue.id,
        room_number=issue.room_number,
        description=issue.description,
        priority=issue.priority,
        status=issue.status,
        assigned_to=issue.assigned_to,
        created_at=issue.created_at.isoformat(),
        started_at=issue.started_at.isoformat() if issue.started_at else None,
        completed_at=issue.completed_at.isoformat() if issue.completed_at else None
    )


def _technician_to_response(t: TechnicianModel) -> TechnicianResponseSchema:
    return TechnicianResponseSchema(
        employee_id=t.employee_id,
        full_name=t.full_name,
        shift=t.shift,
        specialization=t.specialization,
        is_available=t.is_available,
        resolved_count=t.resolved_count
    )
