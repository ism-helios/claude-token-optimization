# Playbook

Habits ranked by measured saving against real history. Do them in this order —
the top three carry almost all the benefit.

| # | Habit | Saving | Effort to adopt |
| - | ----- | ------ | --------------- |
| 1 | Cap session context at ~200K | 34.3% | Medium — needs a new reflex |
| 2 | Route work by phase to the right model | 27.2% | Low — one choice per session |
| 3 | Never use Fable 5 (use Fable 5.1 or Opus 5) | 18.4% | Trivial |
| 4 | Trim tool output | ~5–10% | Low — one-time `CLAUDE.md` |
| 5 | `@`-mention files instead of describing them | small | Trivial |
| 6 | Prune loaded MCP servers | small, compounding | One-time |
| 7 | Lower effort for mechanical work | ~1–2% | Trivial |

Target: a **43% cut** turns a 4-day allowance into a 7-day one. Items 1–3
together measure **52.4%**.

---

## 1. Cap session context at ~200K

**The single biggest lever.** 21 sessions were 55.5% of all consumption purely
by being long.

The reflex: **one task, one session.**

```
/context     # check where you are
/clear       # task finished, or context > 200K
/compact     # mid-task but bloated, and you need the thread
```

`/clear` vs `/compact`:

- **`/clear`** — task is done. Full reset, cheapest possible next turn.
- **`/compact`** — still mid-task. Summarizes, keeping the thread. Costs a
  summarization pass but collapses the context. Run it *while the cache is warm*
  (within the hour), not after a long break.

Practical triggers:

- Context passes ~200K → compact or clear
- A test suite goes green → clear before the next task
- You switch files/features/goals → clear
- You come back after lunch (cache is cold anyway) → clear
- **Before starting any long autonomous loop** → clear first, so the loop's turns
  are not dragging unrelated history

For parallel worktrees: worktrees are fine, but treat each one as a session that
must also stay under the cap. Thirty worktrees at 1M context each is thirty
times the waste, not one.

## 2. Route by phase, not by habit

Full table in [04-model-routing.md](04-model-routing.md). The summary:

- **Sonnet 5** — issues, bug reports, PR descriptions, commit messages, docs,
  codebase search, mechanical refactors, test scaffolding
- **Opus 5** — planning, implementation, hard debugging, code review, anything
  where a wrong decision is expensive
- **Haiku 4.5** — bulk mechanical passes, log triage
- **Fable 5.1** — genuinely hard reasoning only; it is 2× Opus per token
- **Fable 5** — never; strictly worse than 5.1 at the same price

**Set the model before the first turn.** Switching mid-session invalidates the
cache and re-bills everything at write price — see
[02-cost-model.md](02-cost-model.md#what-invalidates-the-cache).

## 3. Drop Fable 5

Fable 5 was 36.5% of consumption at 2× Opus 5's rate, with cache reads 4× more
expensive than Fable 5.1's. If the Fable tier is genuinely needed, use **5.1**.
Otherwise use Opus 5. Free 18.4%, no behavior change.

## 4. Trim tool output

The largest 1% of tool results were 58.7% of all tool-result content. Each one
is re-read on every later turn in the session.

```bash
npm test 2>&1 | tail -30                  # not the whole run
npm run build --silent
git log --oneline -20                      # not full history
grep -rn "pattern" src/ | head -50
docker compose logs --tail=50
pytest -q                                  # quiet reporter
```

For genuinely large output, write it to a file and grep it, rather than piping it
through context:

```bash
npm test > /tmp/test.log 2>&1; grep -E "FAIL|Error" /tmp/test.log | head -40
```

Or run the noisy thing **in a subagent** — the subagent's context is separate and
only its conclusion returns to the main thread. Encode your project's preferred
flags once in `CLAUDE.md` (see
[`instructions/CLAUDE.md.template`](../instructions/CLAUDE.md.template)).

## 5. `@`-mention files

`@src/auth/session.ts` attaches the file directly. Describing it instead
("the session file in auth") makes Claude search, then read — two tool round
trips and their results both land in context permanently.

## 6. Prune loaded MCP servers

Every enabled MCP server injects its tool schemas into the system prefix of
**every** session, whether used or not. That is fixed overhead re-read on every
turn.

```
/context     # see what the prefix actually contains
/mcp         # disable what this project doesn't need
```

Toggle them **between** sessions, never during — it changes the tool list and
invalidates the cache.

## 7. Lower effort for mechanical work

`/effort medium` or `low` for renames, formatting, scaffolding. Real but small
(thinking was only 1.7% of consumption) — do it for latency as much as cost.

Like model choice: **set it before the session starts.**

---

## Anti-patterns

Things that feel frugal but are not:

| Anti-pattern | Why it's wrong |
| ------------ | -------------- |
| Turning thinking off to save tokens | Thinking is 1.7% of consumption. On Opus 5 it also causes tool calls to leak into visible text. Lower the *effort* instead. |
| Switching to Sonnet mid-session to "save the rest" | Invalidates the cache; re-bills the whole context at 12.5× the read rate. Costs more than it saves. |
| Very short prompts to save input tokens | Fresh input is **0.0%** of consumption. Under-specifying causes more turns, and turns are what cost money. Write the full task spec up front. |
| Avoiding subagents to avoid extra calls | Subagents have separate context. Delegating a reading-heavy sweep *reduces* main-thread context permanently. |
| Letting one session run all day because "the cache is warm" | Warm cache is 0.1× rate — but on a context 10× larger. Net loss. |

## Verifying it worked

```bash
python3 tools/analyze_usage.py --days 7 --compare data/baseline-2026-09-09.json
```

Watch these four, not the headline number:

| Metric | Baseline | Target |
| ------ | -------- | ------ |
| Median context per request | 300,614 | < 150,000 |
| % of tokens above 500K context | 53.3% | < 15% |
| Cost share of 1000+ turn sessions | 55.5% | < 20% |
| Sonnet + Haiku share of turns | 0.5% | > 30% |
