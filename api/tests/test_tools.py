import pytest
from sqlalchemy import select

from app.fixtures import create_halo_run
from app.models import Agent, Draft, User, Workspace
from app.tools.registry import TOOLS, ToolContext


async def _ctx(session):
    ws = Workspace(slug="acme", name="Acme")
    session.add(ws)
    await session.flush()
    user = User(workspace_id=ws.id, email="creator@acme.test", role="member")
    session.add(user)
    await session.flush()
    agent = Agent(
        workspace_id=ws.id,
        name="Drafting agent",
        tool_keys=["list_sources", "get_source", "add_section"],
        created_by=user.id,
    )
    session.add(agent)
    await session.flush()
    run = await create_halo_run(session, ws, agent, user)
    return ToolContext(session=session, run=run)


# --- the provided tools ---


async def test_get_source_returns_text(session):
    ctx = await _ctx(session)
    out = await TOOLS["get_source"]({"id": 1}, ctx)
    assert "30 hours" in out["text"]


async def test_add_section_appends_to_draft(session):
    ctx = await _ctx(session)
    out = await TOOLS["add_section"]({"title": "T", "body": "B", "cited_source_ids": [1]}, ctx)
    assert out["ok"] is True
    draft = (
        await session.execute(select(Draft).where(Draft.run_id == ctx.run.id))
    ).scalar_one()
    assert draft.sections[-1]["title"] == "T"


async def test_fetch_reference_rejects_bad_host(session):
    ctx = await _ctx(session)
    with pytest.raises(ValueError):
        await TOOLS["fetch_reference"]({"url": "http://evil.example/x"}, ctx)
