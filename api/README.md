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

Set these in `agent-studio/.env` (see `.env.example`); docker-compose picks it up.

- `DATABASE_URL`: a SQLAlchemy async URL. Defaults to a local SQLite file when unset. `docker-compose.yml` points it at Postgres. The tests override it with in-memory SQLite.
- `ANTHROPIC_API_KEY`: the key the agent's model client reads. Needed to run the agent against a real model; the tests do not use it.
- `ANTHROPIC_MODEL`: which model the agent runs on. Defaults to `claude-opus-5`; `.env.example` ships `claude-haiku-4-5`, which is cheaper and fast enough for this loop.
- `LOG_LEVEL`: `INFO` by default. `DEBUG` adds per-request detail.

## Logs

`docker compose logs -f api` is the first place to look. Every model call (model, turn count, stop reason, token usage), every tool call, and every gate decision is logged, and a run that fails writes the reason into its transcript as an `error` step, so `/runs/{id}/trace` and the run page show it too.

## Health

`GET /health` opens a real database connection. It returns 503 with the driver's error if the database is unreachable, so an api that came up before Postgres was ready reports unhealthy rather than reporting ok and failing on first use. `docker compose` gates the `web` service on it.
