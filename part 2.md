**Part 2 of 7 – Backend (FastAPI) Setup + Core Files**

Copy everything below this line.

---

### Backend Setup

1. Create the backend folder and move into it:
```bash
mkdir -p backend/app/routes
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

3. Create `requirements.txt` and paste this:

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
redis==5.0.8
aiokafka==0.11.0
asyncpg==0.29.0
motor==3.5.1
pydantic==2.8.2
pydantic-settings==2.4.0
python-dotenv==1.0.1
boto3==1.35.0
httpx==0.27.0
```

4. Install the dependencies:
```bash
pip install -r requirements.txt
```

---

### File: `backend/app/config.py`

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    MONGO_URI: str
    MONGO_DB: str = "leaderboard"
    REDIS_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC_SCORE_UPDATES: str = "score.updates"
    SQS_QUEUE_URL: str
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"
    AWS_DEFAULT_REGION: str = "us-east-1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    class Config:
        env_file = "../.env"          # root .env
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

---

### File: `backend/app/models.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ScoreIn(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    points: float = Field(..., ge=0)
    game: Optional[str] = "default"
    metadata: Optional[dict] = None

class LeaderboardItem(BaseModel):
    rank: int
    user_id: str
    points: float

class LeaderboardResponse(BaseModel):
    items: list[LeaderboardItem]
    page: int
    size: int
    total: Optional[int] = None
    links: dict
```

---

### File: `backend/app/redis_client.py`

```python
import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

redis_client: redis.Redis | None = None

async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None

# Leaderboard helpers using Sorted Set
LEADERBOARD_KEY = "leaderboard:global"

async def update_score(user_id: str, points: float) -> None:
    r = await get_redis()
    await r.zadd(LEADERBOARD_KEY, {user_id: points})

async def get_leaderboard(offset: int = 0, limit: int = 20) -> list[tuple[str, float]]:
    r = await get_redis()
    # Highest score first
    return await r.zrevrange(LEADERBOARD_KEY, offset, offset + limit - 1, withscores=True)

async def get_user_rank(user_id: str) -> int | None:
    r = await get_redis()
    rank = await r.zrevrank(LEADERBOARD_KEY, user_id)
    return rank + 1 if rank is not None else None

async def get_total_players() -> int:
    r = await get_redis()
    return await r.zcard(LEADERBOARD_KEY)
```

---

### File: `backend/app/kafka_producer.py`

```python
from aiokafka import AIOKafkaProducer
from app.config import get_settings
import json

settings = get_settings()
producer: AIOKafkaProducer | None = None

async def start_producer():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
    )
    await producer.start()

async def stop_producer():
    global producer
    if producer:
        await producer.stop()
        producer = None

async def send_score_event(payload: dict):
    if producer is None:
        raise RuntimeError("Kafka producer is not started")
    await producer.send_and_wait(
        settings.KAFKA_TOPIC_SCORE_UPDATES,
        json.dumps(payload).encode("utf-8")
    )
```

---

**End of Part 2**

Reply with **`next`** or **`part 3`** to receive the FastAPI routes + main.py + rate limiting.