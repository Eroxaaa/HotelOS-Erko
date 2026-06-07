import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from redis_client import broker, Channels


class DashboardManager:
    """
    WebSocket ulanishlarini boshqaruvchi klass.
    Bir vaqtda bir nechta browser ulanishi mumkin —
    hammasi ro'yxatda saqlanadi.
    """

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[DASHBOARD] Yangi ulanish. Jami: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[DASHBOARD] Ulanish uzildi. Jami: {len(self.active_connections)}")

    async def broadcast(self, data: dict) -> None:
        """
        Barcha ulangan browserlarga xabar yuborish.
        Uzilgan ulanishlar ro'yxatdan chiqariladi.
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(data))
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


manager = DashboardManager()


def setup_broker_listener(loop: asyncio.AbstractEventLoop):
    """
    Broker dan dashboard xabarlarini tinglash.
    Xabar kelganda barcha WebSocket ulanishlariga yuboriladi.
    """
    def on_dashboard_update(data: dict):
        print(f"[DASHBOARD] Broker xabari olindi: {data}")
        future = asyncio.run_coroutine_threadsafe(manager.broadcast(data), loop)

        def on_done(done_future):
            error = done_future.exception()
            if error:
                print(f"[DASHBOARD] Broadcast xatosi: {error}")

        future.add_done_callback(on_done)

    broker.subscribe(Channels.DASHBOARD_UPDATE, on_dashboard_update)
    print("[DASHBOARD] Broker listener sozlandi")
