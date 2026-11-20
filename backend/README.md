# ElderShield Backend

FastAPI + SQLModel + Alembic (Phase 1 + Phase 2 health/audit/threat DNS).

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

Admin UI (Tailwind + HTMX): `http://127.0.0.1:8000/admin/ui/login` (use `ADMIN_API_KEY`)  
API base: `/api/v1`  
UI notes: [`../docs/runbooks/admin-ui.md`](../docs/runbooks/admin-ui.md)

## Test

```bash
python -m pytest -q
```

## Notes

- Schema: `SQLModel.metadata.create_all` + sqlite additive columns in `init_db` (dev/lab)
- Phase 2: device health, threat hosts, allowlist, audit, `ADMIN_NOTIFY_WEBHOOK_URL` — see `docs/releases/v0.2.0.md`
- Operator: Play internal AAB, production threat hosts, NextDNS profile keys
