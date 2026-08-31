### 1. For `pyproject.toml`

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.6",   # ← Correct way
    "redis>=5.0.8",
    "aiokafka>=0.11.0",
    "asyncpg>=0.29.0",
    "motor>=3.5.1",
    "pydantic>=2.8.2",
    "pydantic-settings>=2.4.0",
    "python-dotenv>=1.0.1",
    "boto3>=1.35.0",
    "httpx>=0.27.0",
]
```

---

### 2. For `requirements.txt` (if you still use it)

```txt
uvicorn[standard]>=0.30.6
```

or pinned:

```txt
uvicorn[standard]==0.30.6
```

---

### Quick Install Commands

Using `pyproject.toml`:
```bash
pip install -e .
```

Or directly:
```bash
pip install "uvicorn[standard]"
```

---

Would you like me to give you the **full updated `pyproject.toml`** again with this correctly included (and cleaned up)?