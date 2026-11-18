# ElderShield Backend

FastAPI + SQLModel + Alembic (Phase 1).

## Setup

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

Admin UI: `http://127.0.0.1:8000/admin/ui/login` (use `ADMIN_API_KEY`)

## Test

```bash
python -m pytest -q
```

API base (later): `/api/v1`
