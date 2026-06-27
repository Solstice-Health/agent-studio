from __future__ import annotations

import json

from ..config import LENGTH_BUDGET_CHARS

# A check takes the draft (a Draft row), the run's sources (list of dicts with
# id/title/text), and an LLMClient, and returns (status, detail). Status is one of
# passed | failed | uncertain | errored. The rule checks below ignore the llm; the
# claim-support check is meant to use it.


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
    # TASK 2. This is not a rule. A claim in the draft is supported only if a cited
    # source backs its meaning, not merely its words. A line that reuses a source's
    # words but changes what they mean is not supported; a faithful paraphrase is.
    #
    # Decide how to judge that, implement it here, wire it into the runner next to
    # the rule checks, and report which claims fail and why. You have the run's
    # sources and the LLMClient available.
    raise NotImplementedError("task 2: implement the claim-support check")
