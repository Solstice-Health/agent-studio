# Agent Studio Assignment

An agent drafts content through tools you build, and a gate decides whether the draft can ship. A real model orchestrates; the deterministic tools do the auditable work. You extend a working starter repo — you're not starting from a blank page.

Use AI however you normally do. We're not checking whether you can write a tool loop by hand — we're reading the judgment around it: tools that are clean and correct, and a judge whose decisions you can defend.

## What's in the seed

It's multi-tenant. People belong to a workspace, and a workspace can never reach another workspace's runs or drafts — the read paths are already scoped, and a test pins the boundary.

You don't write any copy. The brief and the sources ship in the seed — a one-pager for the Halo sleep band, backed by three short sources:

- **Spec sheet:** 30 hours of battery, water-resistant to 50m, tracks heart rate and sleep stages.
- **Study summary:** in a 200-person internal study, sleep-stage detection matched a clinical sleep lab 87% of the time.
- **Compliance note:** not a medical device, not meant to diagnose or treat anything.

The recorded run drafts three cited sections from those. One claims "clinically proven sleep tracking," which the sources do not back. Another says "keeps going for more than a day on a charge," which the 30-hour spec does. Telling those apart is the verification tool's job.

## Model versus tools

Read this part closely, it shapes everything else.

- The agent runs on a **real model**, through the `LLMClient` interface. `AnthropicLLM` is the live implementation and you wire it up. That's the product.
- `ScriptedLLM` is a **test double** behind the same interface. The tests inject it so they run with no key and no network. It is not a second way to run the agent.
- The **tools are plain deterministic functions**. The claim-support verification tool grounds a claim in its cited sources and returns inspectable evidence, with no model call. That is what makes judging auditable and unit-testable.

The run loop, the gate runner, and the rule checks ship working. A run goes `created → running → completed`, or `failed` if it hits the step budget. A tool that throws is caught and the error handed back to the agent. A run keeps a transcript — the brief, each model turn, each tool call, each result — and that transcript is the record of truth.

When a run finishes it has a draft, and the draft goes through the gate. Pass every check and it's accepted; fail one and it's blocked, with the reasons attached.

## Your tasks

**1. The tool layer.** Build `verify_claim_support` in `app/tools/verification.py`. Given a claim and the sources it cites, decide whether those sources actually back it, and return the evidence behind the decision. An overstatement is unsupported; a faithful paraphrase is supported; an uncited claim is unsupported. Make `tests/test_tools.py` pass. This is the heart of the exercise and it needs no model.

**2. The gate.** Wire the verification tool in so a draft with an unsupported claim is blocked and the gate reports which claim failed and why. What "uncertain" should do is your call — make it deliberately. The rule checks (disclaimer, length, well-formed sections) are done for you.

**3. The real model.** Implement `AnthropicLLM` (or your provider of choice) so the agent drafts and judges through your tools for real, not just under the test double. The prompts and the tool-use loop are yours to get right. Be ready to run it live and walk us through it, including how you handle a claim the verification tool can't settle.

The rest is for the conversation: surviving a change of model provider, versioning the prompts, how it scales.

## Running it

```bash
docker compose up --build            # postgres, api on :8000, web on :3000
docker compose exec api python seed.py
open http://localhost:3000
```

The tests need neither Postgres nor a key — in-memory SQLite and the scripted double:

```bash
cd api && pip install -r requirements.txt && pytest
```

A live run reads `ANTHROPIC_API_KEY` from the environment. We provide one, so don't spend your own; just don't commit it. Auth is a deliberately simple two-header shim — see `api/README.md` and don't spend time there.

## What's where

```text
api/app/
  tools/         registry + verification.py    <- task 1
  gate/          check runner + checks         <- task 2
  llm/           LLMClient, AnthropicLLM       <- task 3
  routes/        agents, runs, gate
  engine/        the run loop (given)
  fixtures.py    the seeded brief, sources, and scripted run
  models.py      Workspace, User, Agent, Run, RunStep, Draft, CheckResult, Source
api/tests/       some passing, some skipped that point at what to build
web/             Next.js: run view, draft + gate view
```

## Invariants

We run an automated suite against your submission. Change the implementations however you like, but keep these contracts stable — names, locations, signatures, shapes — or the suite can't run:

- `app/tools/verification.py` — `verify_claim_support(claim, cited_sources) -> dict`
- `app/tools/registry.py` — `TOOLS`, `ToolContext`
- `app/engine/loop.py` — `start_run(session, run, llm)`
- `app/gate/runner.py` — `run_gate(session, run, llm=None)`
- `app/gate/checks.py` — `(draft, sources, llm) -> (status, detail)` checks (add freely; don't change existing `check_key`s)
- `app/fixtures.py` — `create_halo_run`, `make_scripted_llm`, `NEVER_FINALIZE_BRIEF`, the Halo section titles
- `app/llm/` — `AnthropicLLM`, and `ScriptedLLM` behind `LLMClient`
- `app/models.py` — `Draft.sections`, `Run`, `CheckResult` field shapes
