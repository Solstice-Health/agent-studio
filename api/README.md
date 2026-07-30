# Agent Studio API

FastAPI + SQLAlchemy (async). The run engine, the gate, and the model client all live under `app/`.

## Running the tests (no Docker needed)

The tests use an in-memory SQLite database and a scripted test double for the model, so you don't need Postgres or an API key for the test loop.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Running the whole thing

From the repo root: `docker compose up --build`, then `docker compose exec api python seed.py`. That uses Postgres.

## Auth (a shim, don't spend time here)

There are no passwords or tokens. Every request carries two headers, and the middleware in `app/middleware.py` turns them into a workspace and a user on the request:

- `X-Workspace-Slug`: the workspace you're acting in, `acme` or `globex`.
- `X-User-Email`: which seeded user you are, resolved within that workspace.

Seeded users:

| Workspace | Member | Admin |
| --------- | ----------------------- | ---------------------- |
| `acme`    | `creator@acme.test`     | `admin@acme.test`      |
| `globex`  | `creator@globex.test`   | `admin@globex.test`    |

Example:

```bash
curl -H "X-Workspace-Slug: acme" -H "X-User-Email: creator@acme.test" localhost:8000/agents
```

## Environment

- `DATABASE_URL`: a SQLAlchemy async URL. Defaults to a local SQLite file when unset. `docker-compose.yml` points it at Postgres. The tests override it with in-memory SQLite.
- `ANTHROPIC_API_KEY`: the key the agent's model client reads. Needed to run the agent against a real model; the tests do not use it.
