from __future__ import annotations

import json

from ..config import LENGTH_BUDGET_CHARS
from ..tools.verification import verify_claim_support

# A check takes the draft (a Draft row), the run's sources (list of dicts with
# id/title/text), and an LLMClient, and returns (status, detail). Status is one of
# passed | failed | uncertain | errored. The rule checks below ignore the llm; a check
# that wants a model is free to use it.


async def required_disclaimer(draft, sources, llm) -> tuple[str, str]:
    text = " ".join(s.get("body", "") for s in draft.sections).lower()
    if "not a medical device" in text:
        return ("passed", "")
    return ("failed", "the draft has no disclaimer")


async def length_budget(draft, sources, llm) -> tuple[str, str]:
    total = len(json.dumps(draft.sections))
    if total <= LENGTH_BUDGET_CHARS:
        return ("passed", "")
    return ("failed", f"draft is {total} chars, over the {LENGTH_BUDGET_CHARS} budget")


async def sections_well_formed(draft, sources, llm) -> tuple[str, str]:
    for i, s in enumerate(draft.sections):
        if not s.get("title") or not s.get("body") or not s.get("cited_source_ids"):
            return ("failed", f"section {i} is missing a title, body, or citation")
    return ("passed", "")


async def claims_supported(draft, sources, llm) -> tuple[str, str]:
    """Ground every section against the sources it cites, via the verification tool.

    One section body is treated as one claim. Any unsupported section fails the check and
    the detail names it, so a blocked draft says which claim it was blocked on.

    "uncertain" does not fail. A claim the tool cannot settle is not the same as a claim
    the sources contradict, and blocking on it would make every ambiguous draft
    unshippable. It is recorded so a human can look; a verdict the tool got wrong is a
    worse outcome than a verdict a person has to read. `run_gate` does block on
    "errored" — a check that could not run has vouched for nothing.
    """
    by_id = {source["id"]: source for source in sources}
    unsupported: list[str] = []
    unsettled: list[str] = []

    for section in draft.sections:
        claim = section.get("body", "")
        if not claim:
            continue
        cited = [by_id[sid] for sid in (section.get("cited_source_ids") or []) if sid in by_id]
        verdict = await verify_claim_support(claim, cited, llm)
        label = f"{section.get('title') or 'untitled'}: {claim!r} - {verdict.get('reason', '')}"
        if verdict.get("status") == "unsupported":
            unsupported.append(label)
        elif verdict.get("status") == "uncertain":
            unsettled.append(label)

    if unsupported:
        return ("failed", "; ".join(unsupported))
    if unsettled:
        return ("uncertain", "; ".join(unsettled))
    return ("passed", "")
