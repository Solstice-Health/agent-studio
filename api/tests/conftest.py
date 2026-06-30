import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (register models on the metadata)
from app.db import Base, get_session
from app.main import app
from app.models import Agent, User, Workspace

DEFAULT_TOOLS = ["list_sources", "get_source", "add_section"]


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def sessionmaker_(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def session(sessionmaker_):
    async with sessionmaker_() as s:
        yield s


@pytest_asyncio.fixture
async def client(sessionmaker_):
    async def override_get_session():
        async with sessionmaker_() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed(sessionmaker_):
    """Factory that inserts a workspace, a user, and optionally an agent, then commits
    and closes its session. Use it for HTTP tests so nothing holds the connection open."""

    async def _seed(slug="acme", with_agent=False, tool_keys=None):
        async with sessionmaker_() as s:
            ws = Workspace(slug=slug, name=slug.title())
            s.add(ws)
            await s.flush()
            user = User(workspace_id=ws.id, email=f"creator@{slug}.test", role="member")
            s.add(user)
            await s.flush()
            agent_id = None
            if with_agent:
                agent = Agent(
                    workspace_id=ws.id,
                    name="Drafting agent",
                    system_prompt="",
                    tool_keys=tool_keys or DEFAULT_TOOLS,
                    created_by=user.id,
                )
                s.add(agent)
                await s.flush()
                agent_id = agent.id
            await s.commit()
            return {"workspace_id": ws.id, "user_id": user.id, "agent_id": agent_id}

    return _seed


def headers(slug="acme"):
    return {"X-Workspace-Slug": slug, "X-User-Email": f"creator@{slug}.test"}
