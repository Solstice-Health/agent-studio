import os

# SQLAlchemy async URL. Defaults to a local SQLite file for convenience; docker-compose
# points this at Postgres, and the tests override it with in-memory SQLite.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./agent_studio.db")

# The gate's length check. Generous; the seeded draft is well under it.
LENGTH_BUDGET_CHARS = 6000

# Hosts the fetch_reference tool is allowed to hit. Anything else raises.
ALLOWED_FETCH_HOSTS = {"docs.internal", "sources.internal"}
