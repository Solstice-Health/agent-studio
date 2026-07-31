from __future__ import annotations

# The claim-support verification tool, and the whole of your task: given a claim and the
# sources it cites, decide whether those sources actually back it, and return the evidence
# behind the decision so the call can be audited.
#
# Everything around this is done. `app/gate/checks.py:claims_supported` already calls this
# for every section of a draft and is wired into the gate, so the moment this returns real
# verdicts the gate starts blocking on them. Two tests in tests/test_gate.py fail until
# then; make them pass.
#
# How you reach the verdict is open — string and structure heuristics, a model, or both.
# The `llm` is the seam: the gate passes its client through, and ScriptedLLM is there to
# inject if you want the tests to exercise a model path offline. Where a claim genuinely
# cannot be settled from the sources, return "uncertain"; the gate records it and does not
# block (see the docstring on claims_supported for why).
#
# The tests for the tool itself are yours to write, and we read them as closely as the
# tool: which cases you thought were worth pinning is most of the signal. Keep them
# runnable with no key and no network. `tests/test_tools.py` shows the house style.


async def verify_claim_support(claim: str, cited_sources: list[dict], llm=None) -> dict:
    # TODO: not implemented. Return a dict shaped like:
    #   {"status": "supported" | "unsupported" | "uncertain", "reason": str, "evidence": list}
    raise NotImplementedError("verify_claim_support is not implemented")
