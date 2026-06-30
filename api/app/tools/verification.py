from __future__ import annotations

# The claim-support verification tool. This is the deterministic core of judging:
# given a claim and the sources it cites, decide whether those sources actually back
# it, and return the evidence behind the decision so the call can be audited.
#
# It is a plain, deterministic function on purpose, so it can be unit-tested without a
# model (see tests/test_tools.py). A live agent can also call it as a tool while it
# judges. Where a claim genuinely cannot be settled from the sources, return
# "uncertain" and let a model make the call; see the assignment.


def verify_claim_support(claim: str, cited_sources: list[dict]) -> dict:
    # TODO: not implemented. Return a dict shaped like:
    #   {"status": "supported" | "unsupported" | "uncertain", "reason": str, "evidence": list}
    raise NotImplementedError("verify_claim_support is not implemented")
