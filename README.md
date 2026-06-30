# Agent Studio Assignment

This is close to the work you'd do here: a real model drafting and judging content through a set of tools you build, and the runtime that has to keep it alive when things go wrong. We've given you a working starter repo to extend, so you're not starting from a blank page.

**Please keep this to about four hours of focused work.** The core done well in that time is a complete submission — we don't expect every task finished. Where you run out of time, a line in DECISIONS.md about what you would reach for next counts for as much as the code. We mean this: do not spend a weekend on it. (Deploying is still required and takes only a few minutes on top of the build — see Deploy.)

## Using AI

Use it. We do, all day. Claude, Cursor, Copilot, whatever you reach for. We're not checking whether you can write a tool loop by hand, because a model will hand you the happy path in a minute.

What we're reading is the judgment around it: tools that are clean and correct, a runtime that survives a tool throwing or the server restarting mid-run, and a judge whose decisions you can actually trust and explain. Put a short note in DECISIONS.md about where you leaned on AI and how you checked it.

## What you're building

An agent drafts content, and a gate decides whether it can ship. The engineering that matters lives in two places: the **tools** the agent uses (to read sources, write cited sections, and verify claims) and the **runtime** that drives the agent and survives failures. A real model orchestrates the tools, and the tools do the deterministic, auditable work.

It's multi-tenant. People belong to a workspace, and a workspace can never reach another workspace's runs or drafts.

## What's in the seed (you don't write any content)

You won't be writing copy or inventing a product. The brief and the sources ship in the seed, and the tests include a recorded run that drafts from them (driven by the test double), so your job is the tools and the runtime, not the words.

The seeded example is a one-pager for a made-up product, the Halo sleep band, aimed at regular consumers. Three short sources back it:

- Spec sheet: 30 hours of battery, water-resistant to 50m, tracks heart rate and sleep stages.
- Study summary: in a 200-person internal study, its sleep-stage detection matched a clinical sleep lab 87% of the time.
- Compliance note: not a medical device, and not meant to diagnose or treat anything.

The recorded run reads those and produces a draft of cited sections. One section claims "clinically proven sleep tracking," which the sources do not back. Another says "keeps going for more than a day on a charge," which the 30-hour spec does back. Telling those apart is the verification tool's job.

## How the model and the tools fit together

Read this part closely, it shapes everything else.

- The agent runs on a real model. It talks to the model through one `LLMClient` interface, and the live implementation is the `AnthropicLLM` adapter you wire up. Running the agent needs an API key (we give you one, see Setup). This is the product: a real model driving the loop.
- The tests do not call the model. They inject `ScriptedLLM`, a deterministic stand-in that replays fixed steps through the same interface, so you can drive the engine and its failure modes with no key and no network. It is a test double, not a second way to run the agent.
- The tools are plain, deterministic functions. The claim-support **verification tool** in particular grounds a claim in its cited sources and returns inspectable evidence, with no model call. That is what makes judging auditable and unit-testable.
- So a real model orchestrates (what to draft, which claims to check) and the deterministic tools do the verifiable work. You build the tools and the runtime; the model is the live engine they run under.

## How a run works

```text
created --start--> running --draft ready--> completed
                     |  ^
     fatal error or  |  |  answer
     budget hit      |  |  arrives
                     v  |
   failed   <---------  needs_input   (waiting on a human; paused, still alive)
   cancelled <--------
```

When a run finishes it has a draft, and the draft goes through the gate. Pass every check and it's accepted. Fail one and it's blocked, with the reasons attached.

What holds throughout:

- A run keeps a transcript: the brief, each model turn, each tool call, each result. The engine appends to it as it goes, and that transcript is the record of truth.
- The loop runs until there's a draft, the step budget is spent, or something fails that you've decided is fatal.
- A run survives a dropped connection and a server restart. Closing the tab and coming back, or killing and restarting the API, must not lose a run or corrupt its transcript.

## What's in the repo

```text
agent-studio/
  api/
    app/
      models.py        Workspace, User, Agent, Run, RunStep, Draft, CheckResult, Source
      middleware.py    workspace + user resolution from request headers
      llm/             LLMClient protocol, AnthropicLLM (real client), ScriptedLLM (test double)
      tools/           the tool registry, the sample tools, and verification.py (the judge's tool)
      gate/            the check runner + the checks
      engine/          the run loop
      routes/          agents, runs, gate
      fixtures.py      the seeded brief, sources, and scripted run
    tests/             some passing, some xfail/skip that point at what to build
    seed.py
  web/                 Next.js: run view, draft + gate view
  docker-compose.yml
```

Start with `api/tests/`, `api/app/tools/`, and `api/app/engine/`.

## Invariants

We run an automated check suite against your submission. Change the implementations however
you like, but keep these contracts stable — names, locations, signatures, and shapes — or the
suite can't run against your code:

- `app/tools/verification.py` — `verify_claim_support(claim, cited_sources) -> dict`
- `app/engine/loop.py` — `start_run(session, run, llm)`, `resume_run(session, run, llm)`
- `app/gate/runner.py` — `run_gate(session, run, llm=None)`
- `app/gate/checks.py` — `(draft, sources, llm) -> (status, detail)` checks (add freely; don't change existing `check_key`s)
- `app/tools/registry.py` — `TOOLS`, `ToolContext`, `SIMULATE_CRASH_ON_SECTION`, `SimulatedCrash`
- `app/fixtures.py` — `create_halo_run`, `make_scripted_llm`, `NEVER_FINALIZE_BRIEF`, the Halo section titles
- `app/llm/scripted.py` — `ScriptedLLM` (test double behind `LLMClient`)
- `app/llm/` — `AnthropicLLM`
- `app/models.py` — `Draft.sections`, `Run`, `CheckResult` field shapes

## Setup

```bash
docker compose up --build       # postgres, api on :8000, web on :3000
docker compose exec api python seed.py
open http://localhost:3000
```

The backend tests run on in-memory SQLite and never call a model, so the test loop needs no Postgres and no key. See `api/README.md`.

To run the agent itself against a real model, put an API key in the environment as `ANTHROPIC_API_KEY`. We provide one for this assignment, so don't spend your own; just don't commit it. Everything except a live run works without it.

The auth shim and the `X-User-Email` and `X-Workspace-Slug` headers are documented in `api/README.md` too; auth is kept simple on purpose, so don't spend time on it.

## Your tasks

**1. The tool layer.** Build the claim-support verification tool in `app/tools/verification.py`. Given a claim and the sources it cites, it decides whether the sources actually back the claim and returns the evidence behind that decision. A claim that overstates its sources is unsupported; a faithful paraphrase is supported; a claim with no backing source is unsupported. Make the unit tests in `tests/test_tools.py` pass, and harden the tools you touch so they validate their inputs and fail clearly. This is the heart of the exercise, and it needs no model.

**2. The run engine.** The loop works on the happy path, but run state sits in memory, so a dropped connection or a restart loses a run in flight, and resume doesn't come back clean. Make runs durable and resumable: a restart mid-run shouldn't lose the run or corrupt its transcript, and a resumed run shouldn't redo work it already did. While you're in there, the loop has no step budget, and one throwing tool takes down the whole run instead of being caught and handed back to the agent. Fix both.

**3. The gate.** Wire the verification tool into the gate so a draft with an unsupported claim is blocked, and the gate reports which claim failed and why. When the verification tool returns "uncertain," what the gate does is yours to decide — make the call deliberately and be ready to defend it. The rule checks (disclaimer, length, well-formed sections) are done for you.

**4. The real model.** The agent runs on a live model through the `AnthropicLLM` adapter. Implement it (Anthropic, or your provider of choice) so the agent drafts and judges through your tools for real, not just under the test double. The prompts and the tool-use loop are yours to get right, and this is where your judgment about working with a real model shows. Be ready to run it live and walk us through it, including how you handle a claim the verification tool can't settle on its own.

**5. Tenant isolation.** One read path lets a workspace reach another's data. Find it, fix it, and add a test that pins the boundary.

**6. Human-in-the-loop.** Make `ask_user` a real pause that survives a restart and resumes on `POST /runs/{id}/answer`.

The rest is for the conversation: keeping this alive across model providers, versioning the prompts, how it scales.

## Deploy

Put a live instance somewhere we can click through. This is a Dockerized API and web UI rather than a static site, so Vercel will not host the backend; a container host fits better (Render, Railway, Fly.io, whatever you like). How you run the model for a hosted demo, a real key or the scripted double the tests use, and how you handle the database, is part of the exercise. Send the live URL.

## What to send back

1. The code. The previously-skipped tests should pass, and add your own for what you build, especially the verification tool and the resume case.
2. A short `DECISIONS.md`: the two or three calls you thought hardest about and the trade-offs, where you used AI and how you checked it, and what you'd do next plus any risk you'd flag before this saw real traffic.
3. Hand it over the way you would to a teammate: a branch, readable commits, and whatever we need to run it.
4. A live URL for the deployed instance, with a line on how you ran it.

## How we read it

We won't be tallying features, and we'll go through your submission with you. In rough order of what counts:

1. **Tool quality.** Is the verification tool correct, clear, and well-tested? Are the tools something the next person could extend without fear?
2. **Correctness under failure.** Does a run survive a restart, a throwing tool, a double resume? Does the gate block what it should?
3. **The live run.** Does the real agent actually draft and judge through your tools, and can you defend the prompts and the judging?
4. **Craft and communication.** Readable diffs, tests that pin the hard cases, and a `DECISIONS.md` that shows your thinking.

Where something is underspecified, make a call, write down why, and keep going. We read that as a good sign.
