import os

# SQLAlchemy async URL. Defaults to a local SQLite file for convenience; docker-compose
# points this at Postgres, and the tests override it with in-memory SQLite.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./agent_studio.db")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# The model the agent runs on. Any id the provider accepts works; see api/README.md.
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")

# Per-turn output cap. Generous for a three-section draft, and low enough that a
# non-streaming request cannot sit past the SDK's HTTP timeout.
ANTHROPIC_MAX_TOKENS = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "16000"))

# The gate's length check. Generous; the seeded draft is well under it.
LENGTH_BUDGET_CHARS = 6000

# Hosts the fetch_reference tool is allowed to hit. Anything else raises.
ALLOWED_FETCH_HOSTS = {"docs.internal", "sources.internal"}
