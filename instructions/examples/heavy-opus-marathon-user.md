# Worked example — heavy Opus user, marathon sessions

A real profile run through
[`GENERATE-MY-INSTRUCTIONS.md`](../GENERATE-MY-INSTRUCTIONS.md) end to end. This
is the same data the repo's research is built on. Included so you can see what
the diagnosis and output look like on real numbers — **not** as something to
copy. Your profile will differ.

**Situation:** Max 20x plan, weekly limit exhausted ~3 days before reset.

---

## Step 1 — Measure

```
93,994 turns across 280 sessions   (28 Jun – 9 Sep 2026, 73 days)
$30,093 API-list-price equivalent  (~$2,886/week)

WHERE IT GOES
  cache reads (re-sending old context)        65.4%
  cache writes (loading new context)          24.3%
  output (answers + thinking)                 10.3%
  fresh input                                  0.0%

MODEL MIX
  claude-opus-5                 51.0%   60,367 turns
  claude-fable-5                36.5%   20,398 turns
  claude-fable-5-1               6.4%    4,932 turns
  claude-opus-4-8                6.1%    7,735 turns
  claude-sonnet-5                0.0%       96 turns
  claude-haiku-4-5               0.0%      416 turns

CONTEXT PER REQUEST
  median 300,614   p90 751,320   max 998,273
  53.3% of tokens spent above 500K context

SESSION LENGTH vs COST
  1-50        78 sessions    0.7% of cost   $0.099/turn
  51-200     102 sessions    3.3% of cost   $0.098/turn
  201-500     42 sessions    7.2% of cost   $0.162/turn
  501-1000    37 sessions   33.3% of cost   $0.372/turn
  1000+       21 sessions   55.5% of cost   $0.405/turn

TOOL BLOAT
  52,809 tool calls; top 3: Bash (35,829), Edit (5,679), Read (2,699)
  largest 1% of tool results = 58.7% of all tool-result content
```

## Step 2 — Diagnosis

| Problem | Verdict | Evidence |
| ------- | ------- | -------- |
| **A. Context bloat** | **Severe** | Cache reads 65.4%; median context 300,614 — 2× the 150K threshold |
| **B. Marathon sessions** | **Severe** | 501+ turn sessions are 88.8% of cost; 1000+ alone are 55.5%. Cost per turn 4× that of short sessions |
| **C. Wrong model tier** | **Severe** | 512 of 93,994 turns (0.5%) on a cheap model, vs a 15% threshold |
| **D. Overpriced tier** | **Severe** | Fable 5 is 36.5% of cost at 2× Opus 5 per token, with cache reads 4× Fable 5.1's |
| **E. Tool-output bloat** | **Confirmed** | Largest 1% of tool results = 58.7% of tool content (threshold 30%). Max single result 825KB |
| **F. Turn inflation** | Not a problem | 17.3 tool calls per user message, under the ~25 threshold |
| **G. Output verbosity** | Not a problem | Output is 10.3%, under 20%. Thinking is only 1.7% of total — cutting it would be pointless |
| **H. Effort mismatch** | Minor | `high` on 94% of turns, but the cost impact is small given G |

Ranked by cost: **B ≈ A > C ≈ D > E > H**. G and F get no rules at all.

## Step 3 — Generated instructions

```text
Token discipline (~65% of my usage is re-reading old context, and sessions over
500 turns are 89% of my consumption — so session length and context size are
what matter):

1. Prompt me to /clear when a task finishes or I switch to unrelated work, and
   to /compact when context passes ~200K mid-task. One line, no lecture.
2. Before any long autonomous run, tell me to /clear first so the loop isn't
   dragging unrelated history.
3. If my current model doesn't fit the work, say so in one line and proceed
   anyway — don't block or ask, and don't raise it twice per session. Sonnet
   fits: issues, PR and commit text, docs, codebase search, mechanical
   refactors, test scaffolding. Opus fits: planning, implementation, hard
   debugging, review. Flag any Fable 5 use — Fable 5.1 costs the same per token
   with 4x cheaper cache reads.
4. Never suggest switching model or effort mid-conversation — it invalidates the
   prompt cache and re-bills the whole context. Tell me to finish, /clear, and
   restart instead.
5. Trim noisy command output by default (| tail -30, --silent, -q, --tail=50).
   For large output, write to a file and grep it rather than piping it through
   context. Never print a whole log or test run when a slice answers it.
6. Delegate read-heavy sweeps to subagents so file dumps stay out of my main
   context. Return the conclusion, not the evidence.
```

Note what's **absent**: no verbosity rule, no "don't think so much", no
turn-count rule. The data said those weren't this user's problem, so spending
instruction-box space on them would weaken the six rules that matter.

## Step 4 — What instructions can't fix

| Action | Measured saving |
| ------ | --------------- |
| `/clear` or `/compact` at ~200K instead of riding to 1M | 34.3% |
| Route ~40% of turns to Sonnet 5 (per session, not per turn) | 27.2% |
| Stop selecting Fable 5; use Fable 5.1 or Opus 5 | 18.4% |
| **200K cap + 40% Sonnet together** | **52.4%** |
| Disable unused MCP servers via `/mcp` (Browser, iOS Simulator were loaded but rarely used) | small, compounds on every turn |
| `/effort medium` for mechanical work | ~1–2% |

Target was a 43% cut to stretch 4 days into 7. The top two clear it.

Re-measure with:

```bash
python3 tools/analyze_usage.py --days 7 --compare data/baseline-2026-09-09.json
```

## Outcome to watch

Not the headline dollar figure — these four:

| Metric | Baseline | Target |
| ------ | -------- | ------ |
| Median context per request | 300,614 | < 150,000 |
| % of tokens above 500K context | 53.3% | < 15% |
| Cost share of 1000+ turn sessions | 55.5% | < 20% |
| Sonnet + Haiku share of turns | 0.5% | > 30% |
