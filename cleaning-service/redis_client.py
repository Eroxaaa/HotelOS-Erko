import os
import redis
import json
import threading
import asyncio
import inspect
from typing import Callable

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class MessageBroker:
    def __init__(self):
        self.pubsub = redis_client.pubsub()
        self.subscribers: dict[str, list[Callable]] = {}
        self._listener_thread = None
        self._event_loop = None

    def publish(self, channel: str, data: dict) -> None:
        message = json.dumps(data)
        redis_client.publish(channel, message)
        print(f"[BROKER] '{channel}' kanaliga xabar yuborildi: {data}")

    def subscribe(self, channel: str, handler: Callable) -> None:
        if channel not in self.subscribers:
            self.subscribers[channel] = []
            self.pubsub.subscribe(channel)
        self.subscribers[channel].append(handler)
        print(f"[BROKER] '{channel}' kanaliga obuna bo'lindi")

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._event_loop = loop

    def _listen(self) -> None:
        for message in self.pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"]
                try:
                    data = json.loads(message["data"])
                except json.JSONDecodeError:
                    print(f"[BROKER] Xato: JSON parse qilinmadi")
                    continue
                if channel in self.subscribers:
                    for handler in self.subscribers[channel]:
                        try:
                            result = handler(data)
                            if inspect.isawaitable(result):
                                if self._event_loop and self._event_loop.is_running():
                                    asyncio.run_coroutine_threadsafe(result, self._event_loop).result()
                                else:
                                    asyncio.run(result)
                        except Exception as e:
                            print(f"[BROKER] Handler xatosi: {e}")

    def start(self) -> None:
        self._listener_thread = threading.Thread(
            target=self._listen,
            daemon=True
        )
        self._listener_thread.start()
        print("[BROKER] Xabar brokeri ishga tushdi")


broker = MessageBroker()


class Channels:
    ROOM_VACATED = "room.vacated"
    ROOM_CLEANED = "room.cleaned"
    ROOM_CLEANING_STARTED = "room.cleaning_started"
    MAINTENANCE_REQUEST = "maintenance.request"
    MAINTENANCE_COMPLETED = "maintenance.completed"
    ROOM_ORDER = "room.order"
    DASHBOARD_UPDATE = "dashboard.update"
