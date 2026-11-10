# SOC MVP backend

FastAPI modular monolith for the ADR-004..009 prototype. All integrations and response
execution are fixture-backed simulations. The application has no HTTP clients, socket
access, shell execution, endpoint/URL configuration or product credentials. PostgreSQL
is the only supported runtime database; SQLite is supported only in tests.

## Requirements and local setup

- Python 3.12
- PostgreSQL 15+ (the only runtime service)

From `backend/`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
# Configure DATABASE_URL for a local PostgreSQL database.
alembic upgrade head
python seed_demo.py
uvicorn app.main:app --reload
```

OpenAPI UI: `http://127.0.0.1:8000/docs`; OpenAPI JSON: `/openapi.json`.
Liveness is `/api/v1/health/live`; readiness checks PostgreSQL only.

Demo `user_key` catalog (no passwords/secrets): `analyst-a`, `admin-a`,
`operator-a`, `auditor-a`, `observer-a`, `analyst-b`, `admin-b`, `operator-b`,
`super-admin`.
Login with `POST /api/v1/auth/mock-login`, then send the returned opaque bearer token
and `X-Organization-ID`. Mock login requires `APP_ENV=development` and
`MOCK_AUTH_ENABLED=true`. Sessions are in-memory and invalidated by process restart.
These fixtures are not a production identity provider.

Response execution is disabled by default. To test the simulation gate locally, set
`RESPONSES_ENABLED=true`; execution remains `simulate_containment` only and never
contacts or modifies a system. Fixture events use documentation-only addresses and
reserved `.test` names. Four providers are available: `wazuh`, `rspamd`, `clamav`,
and `misp`.

## Checks

```powershell
pytest
ruff check app tests migrations
```

## Architecture

`app/core` contains configuration, errors and auth/tenant dependencies; `app/db`
contains SQLAlchemy mappings/session; `app/connectors` contains immutable fixture
connectors; `app/modules` names the domain boundaries; `app/services.py` implements
transactional application use cases; `app/api.py` is an HTTP/DTO adapter only.
Alembic schema changes are under `migrations/`.

Every tenant-scoped service reads/writes by `(organization_id, id)` and tenant context
is derived from a verified active membership. A missing selection is rejected when
multiple memberships exist. Cross-tenant IDs return 404. The event identity constraint
is `(organization_id, source, external_event_id)`. Collection, event persistence,
correlation, incident links, proposal and audit are committed as one database
transaction. The API has bounded `limit` 1..100 and JSON success/error envelopes.

This MVP deliberately defers RabbitMQ, Redis, OpenSearch, OIDC, real connectors,
report exports, and production-grade rate limiting. This is a runnable prototype, not
a production security certification.
