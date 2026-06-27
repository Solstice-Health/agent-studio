from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from ..config import ALLOWED_FETCH_HOSTS
from ..models import Draft, Source


class SimulatedCrash(BaseException):
    """Stands in for the process dying mid-run. It is a BaseException on purpose, so
    ordinary tool-error handling (``except Exception``) does not swallow it. Only the
    task 1 resume fixture triggers it; real tools never raise it."""


# Test hook for the task 1 resume fixture. When set to a section title, add_section
# writes that section to the database and then raises SimulatedCrash, mimicking the
# process dying right after a side effect but before the engine records the result.
# Tests set this; nothing else does.
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
        # The section is committed, but the engine has not recorded the tool result
        # yet. This is the crash window task 1 has to survive on resume.
        await ctx.session.commit()
        raise SimulatedCrash(f"crash after writing section {section['title']!r}")

    return {"ok": True, "section_title": section["title"]}


async def _ask_user(args: dict, ctx: ToolContext) -> dict:
    # SEED STUB: this blocks in memory and cannot survive a restart. Making it a
    # durable pause that resumes on an answer is a stretch task.
    raise NotImplementedError("ask_user is a stub; make it a durable, resumable pause")


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
