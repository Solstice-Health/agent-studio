# Agent Studio Assignment

An agent drafts content through tools, and a gate decides whether the draft can ship. A real model orchestrates; the tools do the work you can audit. The repo runs end to end as shipped — you add one tool.

Use AI however you normally do. We're not checking whether you can write a tool loop by hand — we're reading the judgment around the tool: whether it's correct on cases you weren't shown, and whether you can defend its verdicts.

## What's in the seed

Everything works. `docker compose up`, seed, click "Start a run", and a live model reads the sources and writes a cited draft. The gate then runs four checks over it; three pass and one reports that the verification tool isn't implemented. That last check is your task.

It's multi-tenant. People belong to a workspace, and a workspace can never reach another workspace's runs or drafts — the read paths are scoped and a test pins the boundary.

You don't write any copy. The brief and the sources ship in the seed — a one-pager for the Halo sleep band, backed by three short sources:

- **Spec sheet:** 30 hours of battery, water-resistant to 50m, tracks heart rate and sleep stages.
- **Study summary:** in a 200-person internal study, sleep-stage detection matched a clinical sleep lab 87% of the time.
- **Compliance note:** not a medical device, not meant to diagnose or treat anything.

The recorded run drafts three cited sections from those. One claims "clinically proven sleep tracking," which the sources do not back. Another says "keeps going for more than a day on a charge," which the 30-hour spec does. Telling those apart is the verification tool's job.

## Model versus tools

Read this part closely, it shapes everything else.

- The agent runs on a **real model**, through the `LLMClient` interface. `AnthropicLLM` is the live implementation and it's wired up and working.
- `ScriptedLLM` is a **test double** behind the same interface. The tests inject it so they run with no key and no network. It is not a second way to run the agent.
- The **tools do the checkable work**. The claim-support verification tool grounds a claim in its cited sources and returns inspectable evidence, so a gate decision can be audited rather than taken on trust. How it reaches that verdict — heuristics, a model, or both — is your call.

The run loop, the gate, the rule checks, and the model client all ship working. A run goes `created → running → completed`, or `failed` if it hits the step budget or the model client raises. A tool that throws is caught and the error handed back to the agent. A run keeps a transcript — the brief, each model turn, each tool call, each result, and any error — and that transcript is the record of truth.

## Your task

**Build `verify_claim_support` in `app/tools/verification.py`.** Given a claim and the sources it cites, decide whether those sources actually back it, and return the evidence behind the decision. An overstatement is unsupported; a faithful paraphrase is supported; an uncited claim is unsupported. How you decide is open — heuristics, a model, or both — so long as the verdict comes with evidence someone else could check.

That's the whole assignment. Everything downstream is already wired: `app/gate/checks.py:claims_supported` calls your tool for every section of a draft and is registered in the gate, so the moment it returns real verdicts the gate starts blocking on them. Two tests in `tests/test_gate.py` fail until then — `pytest` shows you exactly which.

**The tests for the tool are yours to write**, and we read them as closely as the tool: which cases you thought were worth pinning is most of the signal. `tests/test_tools.py` shows the house style on the provided tools. Keep them runnable with no key and no network — `ScriptedLLM` is there to inject if your verifier wants a model.

Be ready to run it live and walk us through it. The rest is for the conversation: what a claim you can't settle should do (the seed records `uncertain` and doesn't block — argue with that call if you disagree), surviving a change of model provider, versioning the prompts, how it scales.

## Running it

```bash
cp .env.example .env                 # then paste in the key we sent you
docker compose up --build            # postgres, api on :8000, web on :3000
docker compose exec api python seed.py
open http://localhost:3000
```

Click "Start a run" and watch the transcript stream. `docker compose logs -f api` shows every model call, tool call, and gate decision.

The tests need neither Postgres nor a key — in-memory SQLite and the scripted double:

```bash
cd api && pip install -r requirements.txt && pytest
```

A live run reads `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` from the environment. We provide a key, so don't spend your own; `.env` is gitignored, so just don't move it. Auth is a deliberately simple two-header shim — see `api/README.md` and don't spend time there.

## What's where

```text
api/app/
  tools/         registry + verification.py    <- your task
  gate/          check runner + checks (given, wired)
  llm/           LLMClient, AnthropicLLM, ScriptedLLM (given, working)
  routes/        agents, runs, gate
  engine/        the run loop (given)
  fixtures.py    the seeded brief, sources, and scripted run
  models.py      Workspace, User, Agent, Run, RunStep, Draft, CheckResult, Source
api/tests/       all pass except the two claim-support tests that are your target
web/             Next.js: run view, draft + gate view
```

## Invariants

We run an automated suite against your submission. Change the implementations however you like, but keep these contracts stable — names, locations, signatures, shapes — or the suite can't run:

- `app/tools/verification.py` — `async verify_claim_support(claim, cited_sources, llm=None) -> dict`
- `app/tools/registry.py` — `TOOLS`, `ToolContext`
- `app/engine/loop.py` — `start_run(session, run, llm)`
- `app/gate/runner.py` — `run_gate(session, run, llm=None)`
- `app/gate/checks.py` — `(draft, sources, llm) -> (status, detail)` checks (add freely; don't change existing `check_key`s)
- `app/fixtures.py` — `create_halo_run`, `make_scripted_llm`, `NEVER_FINALIZE_BRIEF`, the Halo section titles
- `app/llm/` — `AnthropicLLM`, and `ScriptedLLM` behind `LLMClient`
- `app/models.py` — `Draft.sections`, `Run`, `CheckResult` field shapes
