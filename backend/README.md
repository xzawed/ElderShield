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

Copy `.env.example` → `.env` and set **distinct** `ADMIN_API_KEY` / `DEVICE_API_KEY`  
(not `change-me-*`). Local escape: `ELDERSHIELD_ALLOW_INSECURE_DEFAULTS=1`.

```bash
uvicorn app.main:app --reload
```

Admin UI: `http://127.0.0.1:8000/admin/ui/login` (use `ADMIN_API_KEY`)  
API base: `/api/v1`

## Test

```bash
python -m pytest -q
```

## Known Phase-1 gaps

- Alembic `versions/` still empty — schema via `SQLModel.metadata.create_all` (dev)
- Play internal track / real-device checklist = S6.1 (user)
