# Dashboard v1.0

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from redis_client import broker
from websocket_handler import manager, setup_broker_listener


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[DASHBOARD] Servis ishga tushmoqda...")
    loop = asyncio.get_running_loop()
    broker.set_event_loop(loop)
    setup_broker_listener(loop)
    broker.start()
    print("[DASHBOARD] Servis tayyor")
    yield
    print("[DASHBOARD] Servis to'xtatilmoqda...")


app = FastAPI(
    title="HotelOS — Dashboard",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def get_dashboard():
    """Dashboard HTML ni qaytarish"""
    with open("/app/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint.
    Browser ulanganida ro'yxatga olinadi,
    uzilganida ro'yxatdan chiqariladi.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Browserdan xabar kutamiz
            # (ping/pong yoki boshqa buyruqlar uchun)
            data = await websocket.receive_text()
            print(f"[DASHBOARD] Browser xabari: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "dashboard",
        "active_connections": len(manager.active_connections)
    }
