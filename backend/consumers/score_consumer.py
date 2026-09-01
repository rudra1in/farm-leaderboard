from functools import lru_cache
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from confluent_kafka import Consumer, KafkaError, KafkaException
import redis.asyncio as redis
import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings, SettingsConfigDict


# ============================================================
# Settings
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    DATABASE_URL: str
    MONGO_URI: str
    MONGO_DB: str = "leaderboard"
    REDIS_URL: str

    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC_SCORE_UPDATES: str = "score.updates"
    KAFKA_GROUP_ID: str = "score-consumer-group"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "../../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

logger = logging.getLogger("score_consumer")


# ============================================================
# Global connections
# ============================================================

redis_client: redis.Redis | None = None
pg_pool: asyncpg.Pool | None = None
mongo_client: AsyncIOMotorClient | None = None

LEADERBOARD_KEY = "leaderboard:global"


# ============================================================
# Connection initialization
# ============================================================

async def init_connections():
    global redis_client, pg_pool, mongo_client

    # --------------------------------------------------------
    # Redis
    # --------------------------------------------------------

    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    # Optional connectivity check
    await redis_client.ping()

    logger.info("Connected to Redis")


    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    db_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )

    logger.info("Connecting to PostgreSQL")

    pg_pool = await asyncpg.create_pool(
        db_url,
        min_size=1,
        max_size=10,
        command_timeout=30,
    )

    logger.info("Connected to PostgreSQL")


    # Create table/indexes

    async with pg_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                points DOUBLE PRECISION NOT NULL,
                game VARCHAR(100) DEFAULT 'default',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_scores_user_id
            ON scores(user_id);

            CREATE INDEX IF NOT EXISTS idx_scores_points
            ON scores(points DESC);
            """
        )


    # --------------------------------------------------------
    # MongoDB
    # --------------------------------------------------------

    mongo_client = AsyncIOMotorClient(
        settings.MONGO_URI
    )

    # Optional connectivity check
    await mongo_client.admin.command("ping")

    logger.info("Connected to MongoDB")

    logger.info("All connections initialized successfully")


# ============================================================
# Connection cleanup
# ============================================================

async def close_connections():
    global redis_client, pg_pool, mongo_client

    if redis_client:
        await redis_client.close()

    if pg_pool:
        await pg_pool.close()

    if mongo_client:
        mongo_client.close()

    logger.info("Connections closed")


# ============================================================
# Business Logic
# ============================================================

async def process_score_event(data: dict):

    user_id = data["user_id"]
    points = float(data["points"])
    game = data.get("game", "default")

    metadata = data.get("metadata", {})

    timestamp = data.get(
        "timestamp",
        datetime.now(timezone.utc).timestamp(),
    )

    event_time = datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    )

    processed_at = datetime.now(timezone.utc)


    # --------------------------------------------------------
    # 1. Redis - live leaderboard
    # --------------------------------------------------------

    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")

    await redis_client.zadd(
        LEADERBOARD_KEY,
        {
            user_id: points
        }
    )

    logger.info(
        "Redis updated -> user_id=%s points=%s",
        user_id,
        points,
    )


    # --------------------------------------------------------
    # 2. PostgreSQL - official record
    # --------------------------------------------------------

    if pg_pool is None:
        raise RuntimeError("PostgreSQL pool is not initialized")

    async with pg_pool.acquire() as conn:

        await conn.execute(
            """
            INSERT INTO scores (
                user_id,
                points,
                game,
                created_at
            )
            VALUES ($1, $2, $3, $4)
            """,
            user_id,
            points,
            game,
            event_time,
        )

    logger.info(
        "PostgreSQL inserted -> user_id=%s",
        user_id,
    )


    # --------------------------------------------------------
    # 3. MongoDB - raw event
    # --------------------------------------------------------

    if mongo_client is None:
        raise RuntimeError("MongoDB client is not initialized")

    db = mongo_client[settings.MONGO_DB]

    await db.score_events.insert_one(
        {
            "user_id": user_id,
            "points": points,
            "game": game,
            "metadata": metadata,
            "timestamp": event_time,
            "processed_at": processed_at,
        }
    )

    logger.info(
        "MongoDB event stored -> user_id=%s",
        user_id,
    )


# ============================================================
# Kafka Consumer configuration
# ============================================================

def create_kafka_consumer() -> Consumer:

    config = {
        "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,

        "group.id": settings.KAFKA_GROUP_ID,

        # Start from earliest available message
        # when no committed offset exists.
        "auto.offset.reset": "earliest",

        # IMPORTANT:
        # We commit only after successful processing.
        "enable.auto.commit": False,

        # Store offset only when we explicitly commit.
        "enable.auto.offset.store": False,

        # Consumer should identify itself.
        "client.id": "score-consumer",

        # Maximum time between polls.
        "max.poll.interval.ms": 300000,

        # Heartbeat/session settings.
        "session.timeout.ms": 45000,
        "heartbeat.interval.ms": 15000,
    }

    return Consumer(config)


# ============================================================
# Kafka poll
# ============================================================

def poll_message(consumer: Consumer, timeout: float = 1.0):
    """
    confluent_kafka.Consumer.poll() is blocking.

    Run it in a worker thread so the asyncio event loop
    remains responsive.
    """

    return consumer.poll(timeout)


# ============================================================
# Kafka Consumer
# ============================================================

async def consume():

    await init_connections()

    consumer = create_kafka_consumer()

    consumer.subscribe(
        [
            settings.KAFKA_TOPIC_SCORE_UPDATES
        ]
    )

    logger.info(
        "Kafka consumer started. "
        "topic=%s group=%s",
        settings.KAFKA_TOPIC_SCORE_UPDATES,
        settings.KAFKA_GROUP_ID,
    )

    try:

        while True:

            # ------------------------------------------------
            # poll() is blocking, so don't execute it directly
            # on the asyncio event loop.
            # ------------------------------------------------

            msg = await asyncio.to_thread(
                poll_message,
                consumer,
                1.0,
            )

            if msg is None:
                continue


            # ------------------------------------------------
            # Kafka error handling
            # ------------------------------------------------

            if msg.error():

                if msg.error().code() == KafkaError._PARTITION_EOF:

                    logger.info(
                        "Reached end of partition: "
                        "topic=%s partition=%s offset=%s",
                        msg.topic(),
                        msg.partition(),
                        msg.offset(),
                    )

                    continue

                logger.error(
                    "Kafka error: %s",
                    msg.error(),
                )

                continue


            # ------------------------------------------------
            # Decode message
            # ------------------------------------------------

            try:

                raw_value = msg.value()

                if raw_value is None:
                    logger.warning(
                        "Received message with null value"
                    )
                    continue

                data = json.loads(
                    raw_value.decode("utf-8")
                )

                logger.info(
                    "Received Kafka event: "
                    "topic=%s partition=%s offset=%s data=%s",
                    msg.topic(),
                    msg.partition(),
                    msg.offset(),
                    data,
                )


                # ------------------------------------------------
                # Process business logic
                # ------------------------------------------------

                await process_score_event(data)


                # ------------------------------------------------
                # Commit ONLY after successful processing
                # ------------------------------------------------

                await asyncio.to_thread(
                    consumer.commit,
                    msg,
                    False,
                )

                logger.info(
                    "Kafka offset committed: "
                    "topic=%s partition=%s offset=%s",
                    msg.topic(),
                    msg.partition(),
                    msg.offset(),
                )

            except json.JSONDecodeError:

                logger.error(
                    "Invalid JSON message. "
                    "topic=%s partition=%s offset=%s",
                    msg.topic(),
                    msg.partition(),
                    msg.offset(),
                    exc_info=True,
                )

                # Do not commit.
                #
                # NOTE:
                # This means the same bad message can be
                # repeatedly consumed.
                #
                # Production solution:
                # send invalid messages to a DLQ.

            except Exception:

                logger.error(
                    "Error processing Kafka message. "
                    "topic=%s partition=%s offset=%s",
                    msg.topic(),
                    msg.partition(),
                    msg.offset(),
                    exc_info=True,
                )

                # Do not commit.
                #
                # Message will be processed again.


    except asyncio.CancelledError:

        logger.info(
            "Kafka consumer cancellation requested"
        )

    except KafkaException as e:

        logger.error(
            "Kafka exception: %s",
            e,
            exc_info=True,
        )

    finally:

        logger.info("Closing Kafka consumer")

        consumer.close()

        await close_connections()


# ============================================================
# Application entry point
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(consume())

    except KeyboardInterrupt:

        logger.info(
            "Application stopped by user"
        )