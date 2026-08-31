**Part 7 of 7 – Final: Installation Order + How to Run Everything + Testing**

Copy everything below this line.

---

### Final Setup & Run Guide

Follow these steps **in order**.

---

### Step 1: Start Infrastructure (Docker)

From the **root** of the project (`leaderboard-poc/`):

```bash
docker compose up -d
```

Wait 20–40 seconds, then check that everything is healthy:

```bash
docker compose ps
```

You should see `postgres`, `mongo`, `redis`, `kafka`, and `localstack` running.

---

### Step 2: Start the Kafka Consumer

```bash
cd consumers
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python score_consumer.py
```

Leave this terminal open. You should see:
```
All connections initialized
Kafka consumer started. Waiting for messages...
```

---

### Step 3: Start the FastAPI Backend

Open a **new terminal**:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
Starting Kafka producer...
Kafka producer started
Uvicorn running on http://0.0.0.0:8000
```

Test it quickly:
- Open http://localhost:8000/docs
- Or http://localhost:8000/health

---

### Step 4: Start the Astro Frontend

Open a **third terminal**:

```bash
cd frontend
npm run dev
```

Astro will start on: **http://localhost:4321**

---

### Step 5: Test the Full Flow

#### A. Submit some scores

You can use the Swagger UI (http://localhost:8000/docs) or `curl`:

```bash
curl -X POST http://localhost:8000/scores \
  -H "Content-Type: application/json" \
  -d '{"user_id": "player_01", "points": 1500}'

curl -X POST http://localhost:8000/scores \
  -H "Content-Type: application/json" \
  -d '{"user_id": "player_02", "points": 2200}'

curl -X POST http://localhost:8000/scores \
  -H "Content-Type: application/json" \
  -d '{"user_id": "player_03", "points": 1800}'

curl -X POST http://localhost:8000/scores \
  -H "Content-Type: application/json" \
  -d '{"user_id": "player_01", "points": 2500}'
```

Watch the **consumer terminal** — you should see logs for Redis + PostgreSQL + MongoDB updates.

#### B. View the Leaderboard (SSR)

Open in your browser:

- http://localhost:4321/leaderboard
- http://localhost:4321/leaderboard?page=1&size=10

You should see the ranked list rendered via **Astro SSR**.

#### C. Check API directly

- http://localhost:8000/leaderboard
- http://localhost:8000/rank/player_01

---

### Useful Commands Summary

| Service       | Command                                      | Port    |
|---------------|----------------------------------------------|---------|
| Infrastructure| `docker compose up -d`                       | -       |
| Consumer      | `python score_consumer.py`                   | -       |
| Backend       | `uvicorn app.main:app --reload --port 8000`  | 8000    |
| Frontend      | `npm run dev`                                | 4321    |

---

### What this POC demonstrates

- **SSR** with Astro (page is server-rendered on each request)
- **Redis Sorted Sets** as the real-time leaderboard engine
- **Kafka** for asynchronous, durable score processing
- **PostgreSQL** for persistent official records
- **MongoDB** for raw event storage
- Simple **rate limiting** on score submission
- Clean **pagination + links** in the API response
- Separation of concerns matching the original system design diagram

---

### Next Improvements (Optional)

- Add real ISR / on-demand revalidation (webhook from consumer → Astro)
- Replace in-memory rate limiter with Redis-based limiter
- Add authentication
- Add WebSocket for live rank updates
- Deploy frontend to Vercel/Netlify + backend to a server

---

**End of Part 7 – Complete POC**

You now have the full working Proof of Concept.

Would you like me to also provide:
1. A quick troubleshooting guide?
2. Dockerfile versions for backend/frontend?
3. On-demand revalidation example?
4. Or anything else?