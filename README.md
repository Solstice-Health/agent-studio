# Agent Studio Assignment

This is close to the work you'd do here: an agent that drafts content, and the runtime that has to keep it alive when things go wrong. We've given you a working starter repo to extend, so you're not starting from a blank page.

Aim for about 3 to 4 hours. Do the two core tasks properly. The stretch list is optional and we'll talk through whatever you skip, so don't lose a weekend to this. Three things done carefully beats six things rushed.

## Using AI

Use it. We do, all day. Claude, Cursor, Copilot, whatever you reach for. We're not checking whether you can write a tool loop by hand, because a model will hand you the happy path in a minute.

What we're reading is the judgment around it. A tool throws halfway through a run. The API restarts mid-run. The same run gets resumed twice. A check has to judge something a regex can't. Those are the places an AI answer looks right and isn't, and they are where this assignment lives.

Put a short note in DECISIONS.md about where you leaned on AI and how you checked it. "Had it draft the resume logic, then wrote a test that restarts the engine mid-run and caught it re-running a tool that had already run" is the kind of thing we want to see.

## What you're building

An agent drafts content. You hand it a brief and a few approved sources, it reads them through tools, and it builds a draft: a set of sections, each citing the sources it used. Nothing gets accepted until it clears a review gate.

The whole thing is multi-tenant. People belong to a workspace, and a workspace can never reach another workspace's runs or drafts.

## What's in the seed (you don't write any content)

You won't be writing copy or inventing a product. The brief, the sources, and a recorded run that drafts from them all ship in the seed. Your job is the runtime and the gate, not the words.

The seeded example is a one-pager for a made-up product, the Halo sleep band, aimed at regular consumers. Three short sources back it:

- Spec sheet: 30 hours of battery, water-resistant to 50m, tracks heart rate and sleep stages.
- Study summary: in a 200-person internal study, its sleep-stage detection matched a clinical sleep lab 87% of the time.
- Compliance note: not a medical device, and not meant to diagnose or treat anything.

The recorded run reads those and produces a draft of cited sections. Task 2's check then decides whether each claim actually holds up against the sources. "Runs more than a day on a charge" holds up against the 30-hour spec. "Clinically proven sleep tracking" does not, because all we have is an internal 87% study. Every candidate gets the same fixtures.

## How the model is wired in

Read this part closely, it shapes everything else.

Nothing in the app talks to a model directly. Every call goes through one interface:

```python
class LLMClient(Protocol):
    async def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Completion: ...

# A Completion is either a final answer or one or more tool calls to run.
```

In the tests that interface is a `ScriptedLLM` that replays fixed completions, so a run is deterministic and costs nothing. Build against the interface. There's an `AnthropicLLM` stub you can fill in with your own key if you want to watch it run live, but grading uses the scripted version, so don't let correctness depend on a real model. The same client is available wherever you need it, including inside a check.

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
- A human step is a real pause, not glue code. When the agent calls `ask_user`, or the gate needs a person to settle a claim, the run parks in `needs_input` and persists. `POST /runs/{id}/answer` picks it up where it stopped, and a run can pause more than once.
- A run survives a dropped connection and a restart. Close the tab and come back, or kill and restart the API, and the run is still there with its transcript intact.

## What's in the repo

```text
agent-studio/
  api/                 FastAPI + SQLAlchemy + Postgres
    app/
      models.py        Workspace, User, Agent, Run, RunStep, Draft, CheckResult, Source
      middleware.py    workspace + user resolution from request headers
      llm/             LLMClient protocol, ScriptedLLM, AnthropicLLM stub
      tools/           the tool registry + sample tools (one throws)
      gate/            the check runner + the checks (one is missing; see task 2)
      engine/          the run loop (works on the happy path; see task 1)
      routes/          agents, runs, gate
      fixtures.py      the seeded brief, sources, and scripted runs
    tests/             some passing, some xfail/skip that point at what to build
    seed.py            loads two workspaces, agents, sources into the database
  web/                 Next.js (App Router, TS): run view, draft + gate view
  docker-compose.yml   postgres + api + web
```

Start with `api/tests/`, `api/app/engine/`, and `api/app/gate/`.

## Setup

```bash
docker compose up --build       # postgres, api on :8000, web on :3000
docker compose exec api python seed.py
open http://localhost:3000
```

To run the backend tests without Docker, see `api/README.md`. They use an in-memory SQLite database, so you don't need Postgres for the test loop.

Two seeded workspaces (`acme`, `globex`) with users, agents, and sources. The auth shim and the `X-User-Email` and `X-Workspace-Slug` headers are written up in `api/README.md`. Auth is kept simple on purpose, so don't spend time there.

## Your tasks

Do them in order; the second builds on the first. We'd rather see these two done well, with tests, than the stretch list half-finished.

### Core

**1. Make the run engine safe to run in production.** The loop works on the happy path, but run state sits in memory, so a dropped connection or a restart loses a run in flight, and resume doesn't come back clean. Make runs durable and resumable: a restart in the middle of a run shouldn't lose it or corrupt its transcript, and a resumed run shouldn't redo work it already did. While you're in there, two more things need fixing. The loop has no step budget, so a chatty agent runs forever. And one failing tool takes down the whole run, when it should be caught and handed back to the agent. Pay attention to what "clean" means when a run is interrupted in the middle of a step.

**2. Add the claim-support check.** A draft only gets accepted once it passes the gate. The rule checks are written for you: disclaimer present, within a length budget, sections well-formed. One check is missing, and it isn't a rule. Every claim in the draft has to be backed by the sources, by meaning rather than by matching words. A line that borrows a source's words but changes what they mean isn't backed; a faithful paraphrase is. Write it, wire it into the gate, and have it say which claims failed and why. A check doesn't have to be a plain text function, so use whatever the repo gives you.

### Stretch (only if you have time)

- **Tenant isolation.** One read path lets a workspace reach another's data. Find it, fix it, add a test.
- **Human-in-the-loop.** Make `ask_user` a real pause that survives a restart and resumes on `POST /runs/{id}/answer`.
- **The uncertain claim.** The support check won't always be sure. Decide what the gate does then (block, accept, or hold for a human) and make that a deliberate choice.

The rest is for the conversation, no need to build it: keeping this alive across model providers, versioning the prompts behind the agent, how it scales.

## What to send back

1. The code. The skipped tests should pass, and add your own for what you build, especially the resume case and the check.
2. A short `DECISIONS.md`: the two or three calls you thought hardest about and the trade-offs, where you used AI and how you checked it, and what you'd do next, plus anything you'd want flagged before this saw real traffic.
3. Hand it over the way you would to a teammate: a branch, readable commits, and whatever we need to run it.

## How we read it

We won't be tallying features, and we'll go through the submission with you. In rough order of what counts:

1. Does it hold up when things fail? A restart, a throwing tool, a run resumed twice, a gate that should block.
2. Is the design clear? One run engine you can follow, state that lives somewhere on purpose, a gate the next person can add to.
3. Did you reach for the right tool on the check? That one is as much instinct as code.
4. Craft, and how you explain yourself: clean diffs, tests on the hard cases, a `DECISIONS.md` that shows your thinking.

Where something is underspecified, make a call, write down why, and keep going. We read that as a good sign.
