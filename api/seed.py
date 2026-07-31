"""Load two workspaces, their users and agents, and a Halo run for each into the
database. The runs start in 'created' status; they draft once you run the agent against
a real model (see AnthropicLLM). Run with: docker compose exec api python seed.py"""

import asyncio

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.fixtures import create_halo_run
from app.models import Agent, User, Workspace

ALL_TOOLS = ["list_sources", "get_source", "add_section", "fetch_reference"]

# The gate rejects a section with no citation and a claim the sources don't back, so the
# prompt has to ask for both. Without the citation instruction the draft gets blocked on
# well-formedness and never reaches the interesting check.
DRAFTING_PROMPT = """You draft cited marketing content for {company}.

Read every source before you write: call list_sources, then get_source on each one.

Then call add_section once per section of the one-pager. Every section must pass:
- cited_source_ids lists at least one source id the section actually draws from
- every factual claim in the body is backed by one of those cited sources
- claim only what the sources say, at the strength they say it

Include a section carrying the compliance disclaimer verbatim from its source.
Finish with a short plain-text summary of what you drafted."""


async def main() -> None:
    await init_db()
    async with SessionLocal() as session:
        existing = (
            await session.execute(select(Workspace).where(Workspace.slug == "acme"))
        ).scalar_one_or_none()
        if existing is not None:
            print("already seeded")
            return

        acme = Workspace(slug="acme", name="Acme")
        globex = Workspace(slug="globex", name="Globex")
        session.add_all([acme, globex])
        await session.flush()

        users = [
            User(workspace_id=acme.id, email="creator@acme.test", role="member"),
            User(workspace_id=acme.id, email="admin@acme.test", role="admin"),
            User(workspace_id=globex.id, email="creator@globex.test", role="member"),
            User(workspace_id=globex.id, email="admin@globex.test", role="admin"),
        ]
        session.add_all(users)
        await session.flush()

        acme_agent = Agent(
            workspace_id=acme.id,
            name="Drafting agent",
            system_prompt=DRAFTING_PROMPT.format(company="Acme"),
            tool_keys=ALL_TOOLS,
            created_by=users[0].id,
        )
        globex_agent = Agent(
            workspace_id=globex.id,
            name="Drafting agent",
            system_prompt=DRAFTING_PROMPT.format(company="Globex"),
            tool_keys=ALL_TOOLS,
            created_by=users[2].id,
        )
        session.add_all([acme_agent, globex_agent])
        await session.flush()

        # The acme Halo run's three sources are the first Source rows, so they get
        # ids 1, 2, 3, which is what the recorded run cites.
        await create_halo_run(session, acme, acme_agent, users[0])
        # A globex run too, so the tenant-isolation stretch has cross-workspace data.
        await create_halo_run(session, globex, globex_agent, users[2])

        await session.commit()
        print("seeded workspaces acme and globex")


if __name__ == "__main__":
    asyncio.run(main())
