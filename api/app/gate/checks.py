from __future__ import annotations

import json

from ..config import LENGTH_BUDGET_CHARS

# A check takes the draft (a Draft row), the run's sources (list of dicts with
# id/title/text), and an LLMClient, and returns (status, detail). Status is one of
# passed | failed | uncertain | errored. The rule checks below ignore the llm.


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
    # TODO: not implemented. Use the verification tool (app/tools/verification.py) to
    # ground each claim in the sources it cites, and fail the check if any claim is
    # unsupported.
    raise NotImplementedError("claims_supported is not implemented")
