# Claude Token Optimization

Measured research into why a Claude Max 20x plan runs out of weekly allowance in
four days, and the concrete policy that fixes it.

Everything here comes from analyzing **93,994 real assistant turns across 280
sessions** (28 Jun – 9 Sep 2026) from local Claude Code transcripts. No estimates,
no vendor marketing — the counterfactuals are re-priced replays of actual history.

---

## The finding in one table

| Where the plan allowance actually goes | Share |
| -------------------------------------- | ----- |
| **Cache reads** — re-sending conversation history every turn | **65.4%** |
| Cache writes — loading new context | 24.3% |
| Output — answers *and* thinking | 10.3% |
| Fresh input | 0.0% |

Two-thirds of consumption is Claude re-reading context that was already paid for.
Extended thinking — the usual suspect — is **1.7%**.

Three habits cause it:

1. **Marathon sessions.** 21 sessions with 1000+ turns are **55.5% of all
   consumption**. Cost per turn rises with context: `$0.099/turn` in short
   sessions vs `$0.405/turn` in marathons. Median request carries 300K context;
   p90 is 751K; peak was 998K.
2. **Model mix.** Out of 93,994 turns, **512 used a cheap model.** Meanwhile
   Fable 5 — which costs *twice* Opus 5 per token — was 36.5% of spend.
3. **Tool-result bloat.** The largest 1% of tool results are **58.7%** of all
   tool-result content (biggest: 825KB). Untrimmed `Bash` output (35,829 of
   52,809 tool calls) lands in context permanently and is re-read every turn.

## The fix, with measured savings

Each row is a replay of real history under a different habit:

| Change | Saving |
| ------ | ------ |
| `/clear` or `/compact` at ~200K context instead of riding to 1M | **34.3%** |
| Route ~40% of turns to Sonnet 5 | **27.2%** |
| Stop using Fable 5 → Fable 5.1 (same tier, 4× cheaper cache reads) | 18.4% |
| **200K cap + 40% Sonnet** *(recommended)* | **52.4%** |
| 120K cap + 50% Sonnet *(aggressive)* | 64.2% |

Stretching a 4-day allowance across 7 days needs a **43% cut**. The recommended
combination clears it with headroom.

---

## Repo layout

```
docs/01-findings.md        Full research data and methodology
docs/02-cost-model.md      How metering works; pricing; why cache reads dominate
docs/03-playbook.md        The habits, ranked by measured savings
docs/04-model-routing.md   Which model for which phase of work
instructions/              Copy-paste automation (see below)
tools/analyze_usage.py     Re-measurable analyzer — run it yourself
data/                      Baseline snapshots for before/after comparison
```

## Automating it

Two drop-in files so the policy applies without remembering it:

- **[`instructions/claude-user-instructions.md`](instructions/claude-user-instructions.md)**
  — paste into Claude's **Settings → Instructions for Claude**. Applies across
  every chat and Cowork session on the account.
- **[`instructions/CLAUDE.md.template`](instructions/CLAUDE.md.template)** —
  copy into any repo as `CLAUDE.md`. Encodes output-trimming and session-hygiene
  rules that Claude Code reads automatically.

> **The one trap to know:** changing model or effort *mid-conversation* invalidates
> the prompt cache and re-bills the entire context at full write price. Model
> routing must be **per session**, not per turn. See
> [docs/04-model-routing.md](docs/04-model-routing.md).

## Measuring your own usage

```bash
python3 tools/analyze_usage.py
```

Reads `~/.claude/projects/**/*.jsonl` locally. Nothing is uploaded anywhere.

Capture a baseline, then check back in a week:

```bash
python3 tools/analyze_usage.py --days 7 --json data/week-01.json
python3 tools/analyze_usage.py --days 7 --compare data/baseline-2026-09-09.json
```

## A note on the dollar figures

Costs are **API list-price equivalents** computed from transcript token counts.
They are *not* a bill — a Max plan is a flat subscription. They are a proxy for
how the plan meters usage, which is what makes the ratios and counterfactuals
meaningful. The reported total (~$30K over 73 days) says the plan returned roughly
60× its face value; the point is not the absolute number but that **two-thirds of
it was avoidable re-reading**.
