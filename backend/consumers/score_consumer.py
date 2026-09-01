from functools import lru_cache
import asyncio
import json
import logging
from datetime import datetime #,timezone

# from confluent_kafka import Consumer, KafkaException, KafkaError
import redis.asyncio as redis
import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient
#from pydantic_settings import BaseSettings
from pydantic_settings import BaseSettings , SettingsConfigDict
from pathlib import Path


# ---------- Settings ----------
# score_consumer.py
# backend/consumers/score_consumer.py
#
# .env
# poc-web-endtoend/.env

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    DATABASE_URL: str
    MONGO_URI: str
    MONGO_DB: str = "leaderboard"
    REDIS_URL: str

    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC_SCORE_UPDATES: str = "score.updates"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "../../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("score_consumer")

# ---------- Global connections ----------
redis_client: redis.Redis | None = None
pg_pool: asyncpg.Pool | None = None
mongo_client: AsyncIOMotorClient | None = None

LEADERBOARD_KEY = "leaderboard:global"

async def init_connections():
    global redis_client, pg_pool, mongo_client

    # Redis
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    # PostgreSQL
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Connecting to PostgreSQL at {db_url}")
    pg_pool = await asyncpg.create_pool(db_url, min_size=1, max_size=10)
    print(f"Connected successfully to PostgreSQL")
    # Create table if not exists
    async with pg_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                points DOUBLE PRECISION NOT NULL,
                game VARCHAR(100) DEFAULT 'default',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_scores_user_id ON scores(user_id);
            CREATE INDEX IF NOT EXISTS idx_scores_points ON scores(points DESC);
        """)

    # MongoDB
    mongo_client = AsyncIOMotorClient(settings.MONGO_URI)

    logger.info("All connections initialized")

async def close_connections():
    global redis_client, pg_pool, mongo_client
    if redis_client:
        await redis_client.close()
    if pg_pool:
        await pg_pool.close()
    if mongo_client:
        mongo_client.close()
    logger.info("Connections closed")

# ---------- Business Logic ----------
async def process_score_event(data: dict):
    user_id = data["user_id"]
    points = float(data["points"])
    game = data.get("game", "default")
    metadata = data.get("metadata", {})
    timestamp = data.get("timestamp", datetime.utcnow().timestamp())

    # 1. Update Redis Sorted Set (live leaderboard)
    await redis_client.zadd(LEADERBOARD_KEY, {user_id: points})
    logger.info(f"Redis updated → {user_id}: {points}")

    # 2. Insert into PostgreSQL (official record)
    async with pg_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO scores (user_id, points, game)
            VALUES ($1, $2, $3)
            """,
            user_id, points, game
        )
    logger.info(f"PostgreSQL inserted → {user_id}")

    # 3. Insert raw event into MongoDB
    db = mongo_client[settings.MONGO_DB]
    await db.score_events.insert_one({
        "user_id": user_id,
        "points": points,
        "game": game,
        "metadata": metadata,
        "timestamp": datetime.utcfromtimestamp(timestamp),
        "processed_at": datetime.utcnow()
    })
    logger.info(f"MongoDB event stored → {user_id}")

# ---------- Kafka Consumer ----------
async def consume():
    await init_connections()

    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_SCORE_UPDATES,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="score-consumer-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    await consumer.start()
    logger.info("Kafka consumer started. Waiting for messages...")

    try:
        async for msg in consumer:
            try:
                data = json.loads(msg.value.decode("utf-8"))
                logger.info(f"Received event: {data}")
                await process_score_event(data)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
    finally:
        await consumer.stop()
        await close_connections()

if __name__ == "__main__":
    asyncio.run(consume())