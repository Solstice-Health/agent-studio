from __future__ import annotations

# The claim-support verification tool, the core of judging: given a claim and the sources
# it cites, decide whether those sources actually back it, and return the evidence behind
# the decision so the call can be audited.
#
# How it reaches the verdict is open — string and structure heuristics, a model, or both.
# The `llm` is the seam: the gate passes its client through, and ScriptedLLM is there to
# inject if you want the tests to exercise a model path offline. Where a claim genuinely
# cannot be settled from the sources, return "uncertain"; what the gate does with that is
# your call. The tests for this are yours to write.


async def verify_claim_support(claim: str, cited_sources: list[dict], llm=None) -> dict:
    # TODO: not implemented. Return a dict shaped like:
    #   {"status": "supported" | "unsupported" | "uncertain", "reason": str, "evidence": list}
    raise NotImplementedError("verify_claim_support is not implemented")
