from fastapi import APIRouter, Query, HTTPException, Request
from app.models import ScoreIn, LeaderboardResponse, LeaderboardItem
from app.redis_client import get_leaderboard, get_total_players, get_user_rank
from app.kafka_producer import send_score_event
from app.config import get_settings
import time

router = APIRouter(prefix="", tags=["Leaderboard"])

settings = get_settings()

# Very simple in-memory rate limiter (for POC only)
# Key: IP → list of timestamps
rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT = 10          # max requests
RATE_WINDOW = 60         # seconds

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    if ip not in rate_limit_store:
        rate_limit_store[ip] = []

    # Remove old timestamps
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < RATE_WINDOW]

    if len(rate_limit_store[ip]) >= RATE_LIMIT:
        return True

    rate_limit_store[ip].append(now)
    return False

@router.post("/scores", status_code=202)
async def submit_score(payload: ScoreIn, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    if is_rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    # Prepare event
    event = {
        "user_id": payload.user_id,
        "points": payload.points,
        "game": payload.game,
        "metadata": payload.metadata or {},
        "timestamp": time.time()
    }

    # Send to Kafka (async processing)
    try:
        await send_score_event(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue score: {str(e)}")

    return {
        "status": "accepted",
        "message": "Score submitted successfully and is being processed"
    }

@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard_endpoint(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    offset = (page - 1) * size

    raw_items = await get_leaderboard(offset=offset, limit=size)
    total = await get_total_players()

    items = [
        LeaderboardItem(
            rank=offset + idx + 1,
            user_id=user_id,
            points=points
        )
        for idx, (user_id, points) in enumerate(raw_items)
    ]

    links = {
        "self": f"/leaderboard?page={page}&size={size}",
        "next": f"/leaderboard?page={page + 1}&size={size}" if offset + size < total else None,
        "prev": f"/leaderboard?page={page - 1}&size={size}" if page > 1 else None
    }

    return LeaderboardResponse(
        items=items,
        page=page,
        size=size,
        total=total,
        links=links
    )

@router.get("/rank/{user_id}")
async def get_rank(user_id: str):
    rank = await get_user_rank(user_id)
    if rank is None:
        raise HTTPException(status_code=404, detail="User not found on leaderboard")
    return {"user_id": user_id, "rank": rank}
```

---

### File: `backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.redis_client import close_redis
from app.kafka_producer import start_producer, stop_producer
from app.routes.leaderboard import router as leaderboard_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Kafka producer...")
    await start_producer()
    print("Kafka producer started")
    yield
    # Shutdown
    print("Stopping Kafka producer...")
    await stop_producer()
    await close_redis()
    print("Cleanup done")

app = FastAPI(
    title="Leaderboard POC API",
    description="System Design POC – Leaderboard with Kafka + Redis + Astro SSR/ISR",
    version="1.0.0",
    lifespan=lifespan
)

# CORS (allow Astro frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321", "http://127.0.0.1:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leaderboard_router)

@app.get("/")
async def root():
    return {
        "message": "Leaderboard POC API is running",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}