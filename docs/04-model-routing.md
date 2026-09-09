# Model routing policy

Which model for which phase of work.

> ## Read this first
>
> **Route per session, not per turn.**
>
> Changing model or effort mid-conversation invalidates the prompt cache and
> re-bills the entire accumulated context at **cache-write** price — 12.5× the
> cache-read rate. Switching to Sonnet at turn 400 of a 600K session costs more
> than the whole session did.
>
> So the unit of routing is a **session**, and the workflow is:
>
> 1. Decide what phase of work you're in.
> 2. Pick the model. Pick the effort.
> 3. Do that phase.
> 4. `/clear`. Then pick again for the next phase.
>
> This is the same reflex as capping context, so the two habits reinforce each
> other rather than competing.

---

## The routing table

| Phase of work | Model | Effort | Why |
| ------------- | ----- | ------ | --- |
| **Writing issues / bug reports** | **Sonnet 5** | medium | Structured prose over context you already have. No architectural judgment. |
| **PR descriptions, commit messages, changelogs** | Sonnet 5 | low | Summarizing a known diff. |
| **Docs, READMEs, comments** | Sonnet 5 | medium | Writing, not deciding. |
| **Codebase exploration** ("where is X", "how does Y work") | Sonnet 5, **in a subagent** | low | Reading, not deciding — and the subagent keeps the file dumps out of your main context permanently. |
| **Triage / log & stack-trace reading** | Haiku 4.5 | — | High volume, low judgment. |
| **Mechanical refactors** — renames, import moves, formatting | Sonnet 5 | low | Deterministic transforms. |
| **Test scaffolding / boilerplate** | Sonnet 5 | medium | Pattern-following. |
| — | — | — | — |
| **Planning & architecture** | **Opus 5** | high | Decision quality compounds across everything downstream. Cheapest place to spend. |
| **Implementation / coding** | **Opus 5** | high | The core case. `xhigh` for unfamiliar or intricate code. |
| **Hard debugging** | Opus 5 | xhigh | A wrong hypothesis costs many turns, and turns are what cost money. |
| **Code review / security review** | Opus 5 | high | Missing a real bug is the expensive outcome. |
| **Migrations touching many files** | Opus 5 | high | Plan on Opus, then hand mechanical execution to a Sonnet session. |
| — | — | — | — |
| **Genuinely hard reasoning** where Opus 5 has already failed | Fable 5.1 | high | 2× Opus per token. Escalate deliberately, never by default. |
| **Fable 5** | ✗ **never** | — | Same price as 5.1 with 4× more expensive cache reads. Strictly worse. |

## Worked example — a typical feature

```
Session 1   Sonnet 5 / medium    Write the issue: scope, acceptance criteria
            /clear

Session 2   Sonnet 5 / low       "Where does lead assignment happen?"
            (subagent)            → conclusion only, not 40 file dumps
            /clear

Session 3   Opus 5 / high        Plan the change. Full task spec up front.
            /clear

Session 4   Opus 5 / high        Implement. Stop at ~200K context.
            /compact  (mid-task)  or /clear if a slice is done

Session 5   Sonnet 5 / low       Update tests, docs, changelog
            /clear

Session 6   Opus 5 / high        Review the diff before it lands
```

Six focused sessions, each starting cheap, versus one 3,000-turn session at a
1M context. Same work; the measured difference is roughly **4× cost per turn**.

## The judgment rule

When it isn't obvious, ask: **what does a wrong answer cost?**

- Wrong answer is *cheap to spot and fix* (a typo in a doc, an awkward test
  name) → **Sonnet 5**.
- Wrong answer is *expensive* (a bad schema, a subtle race, a security hole, an
  architecture you'll live with) → **Opus 5**.

Downshifting is not about accepting worse work. It is about not paying frontier
rates for prose and pattern-matching so the budget is there when reasoning
genuinely matters.

## Effort levels

| Effort | Use for |
| ------ | ------- |
| `low` | Mechanical edits, summaries, formatting, search |
| `medium` | Routine implementation, docs, tests |
| `high` | Default for real coding and planning |
| `xhigh` | Intricate or unfamiliar code; hard debugging |
| `max` | Correctness matters more than cost — rare |

Baseline was `high` on 94% of turns. `medium` and `low` are underused; that's
free latency as well as free budget. **Set it before the session starts.**

## Subagents

Subagents are a context tool, not just a parallelism tool. Each gets its **own**
context window; only its final report returns to the main thread.

Delegate when a task means reading a lot to answer a little:

- "Find every call site of `assignLead`" → sweep 60 files, return a list
- "Which tests cover the telesales queue?" → return names, not file bodies
- Running a noisy build or test suite → return the failures, not 800KB of log

The read-heavy work is billed once inside the subagent instead of being parked
in your main context and re-read on every later turn. Route subagents to
**Sonnet 5 at low effort** unless the delegated task itself needs judgment.
