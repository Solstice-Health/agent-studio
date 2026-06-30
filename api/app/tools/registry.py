from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from ..config import ALLOWED_FETCH_HOSTS
from ..models import Draft, Source


class SimulatedCrash(BaseException):
    """Used by the resume test fixture to mimic the process dying mid-run. A
    BaseException so normal error handling does not catch it; real tools never raise it."""


# Test hook for the resume fixture. When set to a section title, add_section writes
# that section and then raises SimulatedCrash. Tests set this; nothing else does.
SIMULATE_CRASH_ON_SECTION: str | None = None


@dataclass
class ToolContext:
    session: object
    run: object


async def _list_sources(args: dict, ctx: ToolContext) -> dict:
    rows = (
        await ctx.session.execute(select(Source).where(Source.run_id == ctx.run.id))
    ).scalars().all()
    return {"sources": [{"id": s.id, "title": s.title} for s in rows]}


async def _get_source(args: dict, ctx: ToolContext) -> dict:
    sid = int(args["id"])
    s = (
        await ctx.session.execute(
            select(Source).where(Source.id == sid, Source.run_id == ctx.run.id)
        )
    ).scalar_one_or_none()
    if s is None:
        return {"error": "source not found"}
    return {"id": s.id, "title": s.title, "text": s.text}


async def _add_section(args: dict, ctx: ToolContext) -> dict:
    """Side-effecting: appends a section to the run's draft in the database."""
    draft = (
        await ctx.session.execute(select(Draft).where(Draft.run_id == ctx.run.id))
    ).scalar_one_or_none()
    if draft is None:
        draft = Draft(run_id=ctx.run.id, sections=[])
        ctx.session.add(draft)
        await ctx.session.flush()
    section = {
        "title": args.get("title", ""),
        "body": args.get("body", ""),
        "cited_source_ids": args.get("cited_source_ids", []),
    }
    # Reassign so SQLAlchemy notices the JSON column changed.
    draft.sections = draft.sections + [section]
    await ctx.session.flush()

    if SIMULATE_CRASH_ON_SECTION is not None and section["title"] == SIMULATE_CRASH_ON_SECTION:
        await ctx.session.commit()
        raise SimulatedCrash(f"crash after writing section {section['title']!r}")

    return {"ok": True, "section_title": section["title"]}


async def _ask_user(args: dict, ctx: ToolContext) -> dict:
    # TODO: not implemented.
    raise NotImplementedError("ask_user is not implemented")


async def _fetch_reference(args: dict, ctx: ToolContext) -> dict:
    url = args.get("url", "")
    rest = url.split("://", 1)[-1]
    host = rest.split("/", 1)[0]
    if host not in ALLOWED_FETCH_HOSTS:
        raise ValueError(f"refusing to fetch from a non-allowlisted host: {host!r}")
    return {"url": url, "content": f"(stub reference content for {url})"}


TOOLS = {
    "list_sources": _list_sources,
    "get_source": _get_source,
    "add_section": _add_section,
    "ask_user": _ask_user,
    "fetch_reference": _fetch_reference,
}

TOOL_SPECS = [
    {
        "name": "list_sources",
        "description": "List the sources attached to this run.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_source",
        "description": "Read the full text of a source by id.",
        "parameters": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        },
    },
    {
        "name": "add_section",
        "description": "Append a section to the draft, citing the sources it draws from.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "cited_source_ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["title", "body"],
        },
    },
    {
        "name": "ask_user",
        "description": "Pause the run and ask the human a question.",
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
    {
        "name": "fetch_reference",
        "description": "Fetch an allowlisted reference URL.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]


def tool_specs_for(tool_keys: list | None) -> list:
    keys = set(tool_keys or [])
    chosen = [spec for spec in TOOL_SPECS if spec["name"] in keys]
    return chosen or TOOL_SPECS
