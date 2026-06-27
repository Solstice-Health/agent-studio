"""The seeded content the agent drafts from, plus the scripted runs that drive the
ScriptedLLM. None of this is a candidate decision: the brief, the sources, and the
recorded run are fixed so every candidate is graded on the same material."""

from __future__ import annotations

from .llm.scripted import ScriptedLLM
from .models import Run, Source

HALO_BRIEF = "Draft a short one-pager for the Halo sleep band, for general consumers."

HALO_SOURCES = [
    {
        "title": "Spec sheet",
        "text": "Battery lasts 30 hours on a charge. Water-resistant to 50m. Tracks heart rate and sleep stages.",
    },
    {
        "title": "Study summary",
        "text": "In a 200-person internal study, the band's sleep-stage detection agreed with a clinical sleep lab 87% of the time.",
    },
    {
        "title": "Compliance note",
        "text": "Not a medical device. Not intended to diagnose or treat any condition.",
    },
]


def _tool_step(call_id: str, name: str, arguments: dict) -> dict:
    return {"kind": "tool_calls", "tool_calls": [{"id": call_id, "name": name, "arguments": arguments}]}


# The recorded Halo run: read the sources, then write three cited sections. The draft
# it produces carries the three claim cases the gate is meant to judge.
#   - "Clinically proven sleep tracking"      overstatement, not supported by an internal study
#   - "more than a day on a single charge"    faithful paraphrase of the 30-hour spec
#   - the disclaimer section                  so required_disclaimer passes
# The cited_source_ids assume the Halo sources are the first three Source rows (1, 2, 3),
# which holds in a fresh test database and in the seed.
HALO_SCRIPT = [
    _tool_step("c1", "list_sources", {}),
    _tool_step("c2", "get_source", {"id": 1}),
    _tool_step("c3", "get_source", {"id": 2}),
    _tool_step(
        "c4",
        "add_section",
        {"title": "Sleep, measured", "body": "Clinically proven sleep tracking you can rely on.", "cited_source_ids": [2]},
    ),
    _tool_step(
        "c5",
        "add_section",
        {"title": "Built for daily life", "body": "Keeps going for more than a day on a single charge.", "cited_source_ids": [1]},
    ),
    _tool_step(
        "c6",
        "add_section",
        {"title": "The fine print", "body": "Not a medical device. Not meant to diagnose or treat anything.", "cited_source_ids": [3]},
    ),
    {"kind": "final", "text": "Draft complete."},
]

# A chatty agent that keeps calling a tool and never finalizes, for the step-budget
# task. Long but finite, so it can never hang a test.
NEVER_FINALIZE_BRIEF = "loop forever fixture"
NEVER_FINALIZE_SCRIPT = [_tool_step(f"n{i}", "list_sources", {}) for i in range(60)]

SCRIPTS = {
    "halo sleep band": HALO_SCRIPT,
    "loop forever fixture": NEVER_FINALIZE_SCRIPT,
}

def make_scripted_llm() -> ScriptedLLM:
    return ScriptedLLM(SCRIPTS)


async def create_halo_run(session, workspace, agent, created_by=None) -> Run:
    """Create a run with the Halo brief and attach its three sources."""
    run = Run(
        workspace_id=workspace.id,
        agent_id=agent.id,
        brief=HALO_BRIEF,
        created_by=created_by.id if created_by is not None else None,
        status="created",
    )
    session.add(run)
    await session.flush()
    for src in HALO_SOURCES:
        session.add(Source(workspace_id=workspace.id, run_id=run.id, title=src["title"], text=src["text"]))
    await session.flush()
    return run
