**Part 1 of 7 – Overview + Project Structure + Docker Compose + Environment**

Copy everything below this line.

---

### Leaderboard POC – Overview

**Stack used:**
- Frontend: Astro (SSR + ISR) + React
- Backend: FastAPI
- Cache / Leaderboard: Redis (Sorted Sets)
- Events: Kafka
- Async tasks: SQS (LocalStack for local)
- Databases: PostgreSQL + MongoDB

**Goal of this POC:**
- Users submit scores
- Scores go through Kafka
- Redis maintains the live leaderboard
- PostgreSQL stores official records
- MongoDB stores raw events
- Astro serves the leaderboard page with SSR + ISR

---

### Recommended Project Structure

```bash
leaderboard-poc/
├── docker-compose.yml
├── .env
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── redis_client.py
│   │   ├── kafka_producer.py
│   │   └── routes/
│   │       └── leaderboard.py
│   ├── requirements.txt
│   └── Dockerfile          # optional
├── consumers/
│   ├── score_consumer.py
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   └── leaderboard.astro
    │   └── components/
    │       └── LeaderboardTable.tsx
    ├── astro.config.mjs
    ├── package.json
    └── .env
```

---

### 1. docker-compose.yml

Create a file named `docker-compose.yml` in the root and paste this:

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: leaderboard
      POSTGRES_PASSWORD: leaderboard
      POSTGRES_DB: leaderboard
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  kafka:
    image: bitnami/kafka:3.7
    ports:
      - "9092:9092"
    environment:
      - KAFKA_CFG_NODE_ID=0
      - KAFKA_CFG_PROCESS_ROLES=controller,broker
      - KAFKA_CFG_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093
      - KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      - KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=0@kafka:9093
      - KAFKA_CFG_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092
    volumes:
      - kafka_data:/bitnami/kafka

  localstack:
    image: localstack/localstack:3
    ports:
      - "4566:4566"
    environment:
      - SERVICES=sqs
      - DEBUG=1
    volumes:
      - localstack_data:/var/lib/localstack

volumes:
  postgres_data:
  mongo_data:
  kafka_data:
  localstack_data:
```

---

### 2. Root `.env` file

Create a file named `.env` in the root:

```env
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://leaderboard:leaderboard@localhost:5432/leaderboard

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=leaderboard

# Redis
REDIS_URL=redis://localhost:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_SCORE_UPDATES=score.updates

# SQS (LocalStack)
SQS_QUEUE_URL=http://localhost:4566/000000000000/leaderboard-side-effects
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
```

---

**End of Part 1**

Reply with **`next`** or **`part 2`** and I will send the Backend (FastAPI) setup + requirements + core files.