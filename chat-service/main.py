from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, field_validator

from redis_client import broker, Channels


class ChatMessageCreate(BaseModel):
    sender: str = Field(..., min_length=1, max_length=80, example="Reception")
    message: str = Field(..., min_length=1, max_length=500, example="Room 203 needs towels")
    room_number: Optional[str] = Field(default=None, max_length=10, example="203")

    @field_validator("sender", "message")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text cannot be blank")
        return value


class ChatMessage(ChatMessageCreate):
    id: str
    created_at: str


class ChatManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[CHAT] Yangi ulanish. Jami: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[CHAT] Ulanish uzildi. Jami: {len(self.active_connections)}")

    async def broadcast(self, data: dict) -> None:
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


manager = ChatManager()
messages: list[ChatMessage] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[CHAT] Servis ishga tushmoqda...")
    broker.start()
    print("[CHAT] Servis tayyor")
    yield
    print("[CHAT] Servis to'xtatilmoqda...")


app = FastAPI(
    title="HotelOS - Chat Service",
    description="Internal staff chat for hotel operations",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/api/chat/messages", response_model=ChatMessage)
async def create_message(data: ChatMessageCreate):
    message = ChatMessage(
        id=str(uuid4()),
        sender=data.sender,
        message=data.message,
        room_number=data.room_number,
        created_at=datetime.now().isoformat()
    )
    messages.append(message)
    if len(messages) > 100:
        messages.pop(0)

    event = {
        "event": "chat_message",
        "message_id": message.id,
        "sender": message.sender,
        "message": message.message,
        "room_number": message.room_number,
        "created_at": message.created_at
    }
    broker.publish(Channels.CHAT_MESSAGE, event)
    broker.publish(Channels.DASHBOARD_UPDATE, event)
    await manager.broadcast(event)
    return message


@app.get("/api/chat/messages", response_model=list[ChatMessage])
async def get_messages():
    return messages


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            message = ChatMessageCreate(**data)
            created = await create_message(message)
            await websocket.send_json(created.model_dump())
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "chat-service",
        "active_connections": len(manager.active_connections),
        "messages": len(messages)
    }
