# API Gateway v1.0

import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Servislar manzillari
RECEPTION_URL = os.getenv("RECEPTION_URL", "http://reception-service:8000")
CLEANING_URL = os.getenv("CLEANING_URL", "http://cleaning-service:8000")
ROOM_URL = os.getenv("ROOM_URL", "http://room-service:8000")
MAINTENANCE_URL = os.getenv("MAINTENANCE_URL", "http://maintenance-service:8000")
CHAT_URL = os.getenv("CHAT_URL", "http://chat-service:8000")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[API-GATEWAY] Ishga tushmoqda...")
    yield
    print("[API-GATEWAY] To'xtatilmoqda...")


app = FastAPI(
    title="HotelOS — API Gateway",
    description="Barcha servislar uchun markaziy kirish nuqtasi",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# -------------------------
# Proxy funksiyasi
# -------------------------

async def proxy(request: Request, target_url: str) -> JSONResponse:
    """
    Kelgan so'rovni tegishli servisga yo'naltiradi.
    Method, headers, body — hammasi uzatiladi.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{target_url}{request.url.path}"
        if request.url.query:
            url += f"?{request.url.query}"

        try:
            body = await request.body()
            response = await client.request(
                method=request.method,
                url=url,
                headers={
                    k: v for k, v in request.headers.items()
                    if k.lower() not in ("host", "content-length")
                },
                content=body
            )
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"Servis mavjud emas: {target_url}"
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Servis javob bermadi"
            )


# -------------------------
# Reception routes
# -------------------------

@app.api_route(
    "/api/reception/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def reception_proxy(request: Request, path: str):
    return await proxy(request, RECEPTION_URL)


# -------------------------
# Cleaning routes
# -------------------------

@app.api_route(
    "/api/cleaning/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def cleaning_proxy(request: Request, path: str):
    return await proxy(request, CLEANING_URL)


# -------------------------
# Room Service routes
# -------------------------

@app.api_route(
    "/api/room/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def room_proxy(request: Request, path: str):
    return await proxy(request, ROOM_URL)


# -------------------------
# Maintenance routes
# -------------------------

@app.api_route(
    "/api/maintenance/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def maintenance_proxy(request: Request, path: str):
    return await proxy(request, MAINTENANCE_URL)


# -------------------------
# Chat routes
# -------------------------

@app.api_route(
    "/api/chat/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def chat_proxy(request: Request, path: str):
    return await proxy(request, CHAT_URL)


# -------------------------
# Health check
# -------------------------

@app.get("/health")
async def health_check():
    """Barcha servislar holati"""
    async with httpx.AsyncClient(timeout=5.0) as client:
        services = {
            "reception": f"{RECEPTION_URL}/health",
            "cleaning": f"{CLEANING_URL}/health",
            "room": f"{ROOM_URL}/health",
            "maintenance": f"{MAINTENANCE_URL}/health",
            "chat": f"{CHAT_URL}/health",
        }

        results = {}
        for name, url in services.items():
            try:
                response = await client.get(url)
                results[name] = "ok" if response.status_code == 200 else "error"
            except Exception:
                results[name] = "unavailable"

        overall = "ok" if all(v == "ok" for v in results.values()) else "degraded"

        return {
            "status": overall,
            "services": results
        }
