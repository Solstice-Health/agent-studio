# Agent Studio Assignment

This is close to the work you'd do here: a real model drafting and judging content through a set of tools you build, and the runtime that has to keep it alive when things go wrong. We've given you a working starter repo to extend, so you're not starting from a blank page.

Do the core well. The stretch list is optional, and we'll talk through whatever you skip. We would rather see the core done carefully, with tests, than everything done loosely.

## Using AI

Use it. We do, all day. Claude, Cursor, Copilot, whatever you reach for. We're not checking whether you can write a tool loop by hand, because a model will hand you the happy path in a minute.

What we're reading is the judgment around it: tools that are clean and correct, a runtime that survives a tool throwing or the server restarting mid-run, and a judge whose decisions you can actually trust and explain. Put a short note in DECISIONS.md about where you leaned on AI and how you checked it.

## What you're building

An agent drafts content, and a gate decides whether it can ship. The engineering that matters lives in two places: the **tools** the agent uses (to read sources, write cited sections, and verify claims) and the **runtime** that drives the agent and survives failures. A real model orchestrates the tools, and the tools do the deterministic, auditable work.

It's multi-tenant. People belong to a workspace, and a workspace can never reach another workspace's runs or drafts.

## What's in the seed (you don't write any content)

You won't be writing copy or inventing a product. The brief, the sources, and a recorded run that drafts from them all ship in the seed. Your job is the tools and the runtime, not the words.

The seeded example is a one-pager for a made-up product, the Halo sleep band, aimed at regular consumers. Three short sources back it:

- Spec sheet: 30 hours of battery, water-resistant to 50m, tracks heart rate and sleep stages.
- Study summary: in a 200-person internal study, its sleep-stage detection matched a clinical sleep lab 87% of the time.
- Compliance note: not a medical device, and not meant to diagnose or treat anything.

The recorded run reads those and produces a draft of cited sections. One section claims "clinically proven sleep tracking," which the sources do not back. Another says "keeps going for more than a day on a charge," which the 30-hour spec does back. Telling those apart is the verification tool's job.

## How the model and the tools fit together

Read this part closely, it shapes everything else.

- Anything that needs a model talks to it through one `LLMClient` interface. In the tests it's a `ScriptedLLM` that replays fixed steps, so the runtime is deterministic to test and costs nothing. For a live run, fill in the `AnthropicLLM` adapter with your own key.
- The tools are plain, deterministic functions. The claim-support **verification tool** in particular grounds a claim in its cited sources and returns inspectable evidence, with no model call. That is what makes judging auditable and unit-testable.
- So the model orchestrates (what to draft, which claims to check) and the tools do the verifiable work. A run is deterministic in the tests because the model is scripted and the tools are deterministic; swap in the real adapter and the same code runs against a live model.

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
      llm/             LLMClient protocol, ScriptedLLM, AnthropicLLM adapter
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

## Setup

```bash
docker compose up --build       # postgres, api on :8000, web on :3000
docker compose exec api python seed.py
open http://localhost:3000
```

The backend tests run on in-memory SQLite, so the test loop needs no Postgres. See `api/README.md`. The auth shim and the `X-User-Email` and `X-Workspace-Slug` headers are documented there too; auth is kept simple on purpose, so don't spend time on it.

## Your tasks

### Core

**1. The tool layer.** Build the claim-support verification tool in `app/tools/verification.py`. Given a claim and the sources it cites, it decides whether the sources actually back the claim and returns the evidence behind that decision. A claim that overstates its sources is unsupported; a faithful paraphrase is supported; a claim with no backing source is unsupported. Make the unit tests in `tests/test_tools.py` pass, and harden the tools you touch so they validate their inputs and fail clearly. This is the heart of the exercise, and it needs no model.

**2. The run engine.** The loop works on the happy path, but run state sits in memory, so a dropped connection or a restart loses a run in flight, and resume doesn't come back clean. Make runs durable and resumable: a restart mid-run shouldn't lose the run or corrupt its transcript, and a resumed run shouldn't redo work it already did. While you're in there, the loop has no step budget, and one throwing tool takes down the whole run instead of being caught and handed back to the agent. Fix both.

**3. The gate.** Wire the verification tool into the gate so a draft with an unsupported claim is blocked, and the gate reports which claim failed and why. The rule checks (disclaimer, length, well-formed sections) are done for you.

**4. Run it against a real model.** Fill in the `AnthropicLLM` adapter (or your provider of choice) so the same agent drafts and judges through your tools with a live model. Be ready to run it and walk us through it, including the prompts and how you handle a claim the verification tool can't settle on its own.

### Stretch (optional)

- **Tenant isolation.** One read path lets a workspace reach another's data. Find it, fix it, add a test.
- **Human-in-the-loop.** Make `ask_user` a real pause that survives a restart and resumes on `POST /runs/{id}/answer`.
- **The uncertain claim.** Decide what the gate does when the verification tool returns "uncertain": block, accept, or send it to the model.
- **Tool arguments.** Validate tool arguments against their specs before running them.

The rest is for the conversation: keeping this alive across model providers, versioning the prompts, how it scales.

## What to send back

1. The code. The previously-skipped tests should pass, and add your own for what you build, especially the verification tool and the resume case.
2. A short `DECISIONS.md`: the two or three calls you thought hardest about and the trade-offs, where you used AI and how you checked it, and what you'd do next plus any risk you'd flag before this saw real traffic.
3. Hand it over the way you would to a teammate: a branch, readable commits, and whatever we need to run it.

## How we read it

We won't be tallying features, and we'll go through your submission with you. In rough order of what counts:

1. **Tool quality.** Is the verification tool correct, clear, and well-tested? Are the tools something the next person could extend without fear?
2. **Correctness under failure.** Does a run survive a restart, a throwing tool, a double resume? Does the gate block what it should?
3. **The live run.** Does the real agent actually draft and judge through your tools, and can you defend the prompts and the judging?
4. **Craft and communication.** Readable diffs, tests that pin the hard cases, and a `DECISIONS.md` that shows your thinking.

Where something is underspecified, make a call, write down why, and keep going. We read that as a good sign.
