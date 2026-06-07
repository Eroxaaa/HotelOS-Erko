import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from database import get_db
from models import OrderModel, MenuItemModel, OrderStatus
from schemas import (
    OrderCreateSchema,
    OrderUpdateSchema,
    OrderResponseSchema,
    MenuItemResponseSchema
)

router = APIRouter()


# -------------------------
# Menyu
# -------------------------

@router.get("/menu", response_model=list[MenuItemResponseSchema])
async def get_menu(session: AsyncSession = Depends(get_db)):
    """Barcha menyu elementlari"""
    result = await session.execute(
        select(MenuItemModel).where(MenuItemModel.is_available == True)
    )
    items = result.scalars().all()
    return [
        MenuItemResponseSchema(
            id=i.id,
            name=i.name,
            category=i.category,
            price=i.price,
            is_available=i.is_available
        )
        for i in items
    ]


# -------------------------
# Buyurtmalar
# -------------------------

@router.post("/orders", response_model=OrderResponseSchema)
async def create_order(
    data: OrderCreateSchema,
    session: AsyncSession = Depends(get_db)
):
    """
    Yangi buyurtma yaratish.
    Broker orqali dashboard ga xabar yuboriladi.
    """
    from redis_client import broker, Channels

    total_price = round(data.unit_price * data.quantity, 2)

    order = OrderModel(
        id=str(uuid.uuid4()),
        room_number=data.room_number,
        guest_id=data.guest_id,
        category=data.category,
        item_name=data.item_name,
        quantity=data.quantity,
        unit_price=data.unit_price,
        total_price=total_price,
        status=OrderStatus.PENDING,
        notes=data.notes,
        created_at=datetime.now()
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)

    # Dashboard ga xabar yuborish
    broker.publish(Channels.DASHBOARD_UPDATE, {
        "event": "new_order",
        "room_number": data.room_number,
        "item_name": data.item_name,
        "total_price": total_price,
        "created_at": datetime.now().isoformat()
    })

    return _order_to_response(order)


@router.get("/orders", response_model=list[OrderResponseSchema])
async def get_all_orders(session: AsyncSession = Depends(get_db)):
    """Barcha buyurtmalar"""
    result = await session.execute(select(OrderModel))
    orders = result.scalars().all()
    return [_order_to_response(o) for o in orders]


@router.get("/orders/room/{room_number}", response_model=list[OrderResponseSchema])
async def get_orders_by_room(
    room_number: str,
    session: AsyncSession = Depends(get_db)
):
    """Xona bo'yicha buyurtmalar"""
    result = await session.execute(
        select(OrderModel).where(OrderModel.room_number == room_number)
    )
    orders = result.scalars().all()
    return [_order_to_response(o) for o in orders]


@router.get("/orders/guest/{guest_id}", response_model=list[OrderResponseSchema])
async def get_orders_by_guest(
    guest_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Mehmon bo'yicha buyurtmalar"""
    result = await session.execute(
        select(OrderModel).where(OrderModel.guest_id == guest_id)
    )
    orders = result.scalars().all()
    return [_order_to_response(o) for o in orders]


@router.patch("/orders/{order_id}", response_model=OrderResponseSchema)
async def update_order(
    order_id: str,
    data: OrderUpdateSchema,
    session: AsyncSession = Depends(get_db)
):
    """
    Buyurtma holatini yangilash.
    Delivered bo'lsa vaqt tamg'asi qo'shiladi.
    """
    from redis_client import broker, Channels

    result = await session.execute(
        select(OrderModel).where(OrderModel.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    update_values = {"status": data.status}

    if data.status == OrderStatus.DELIVERED:
        update_values["delivered_at"] = datetime.now()

        broker.publish(Channels.DASHBOARD_UPDATE, {
            "event": "order_delivered",
            "order_id": order_id,
            "room_number": order.room_number,
            "item_name": order.item_name,
            "delivered_at": datetime.now().isoformat()
        })

    await session.execute(
        update(OrderModel)
        .where(OrderModel.id == order_id)
        .values(**update_values)
    )
    await session.commit()

    result = await session.execute(
        select(OrderModel).where(OrderModel.id == order_id)
    )
    updated_order = result.scalar_one()
    return _order_to_response(updated_order)


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Buyurtmani bekor qilish"""
    result = await session.execute(
        select(OrderModel).where(OrderModel.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.status == OrderStatus.DELIVERED:
        raise HTTPException(
            status_code=400,
            detail="Yetkazilgan buyurtmani bekor qilib bo'lmaydi"
        )

    await session.execute(
        update(OrderModel)
        .where(OrderModel.id == order_id)
        .values(status=OrderStatus.CANCELLED)
    )
    await session.commit()

    return {"success": True, "message": "Buyurtma bekor qilindi"}


# -------------------------
# Yordamchi funksiya
# -------------------------

def _order_to_response(order: OrderModel) -> OrderResponseSchema:
    return OrderResponseSchema(
        id=order.id,
        room_number=order.room_number,
        guest_id=order.guest_id,
        category=order.category,
        item_name=order.item_name,
        quantity=order.quantity,
        unit_price=order.unit_price,
        total_price=order.total_price,
        status=order.status,
        notes=order.notes,
        created_at=order.created_at.isoformat(),
        delivered_at=order.delivered_at.isoformat() if order.delivered_at else None
    )