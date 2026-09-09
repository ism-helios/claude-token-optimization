# Claude Token Optimization

Why a Claude Max plan can run out of weekly allowance in four days, what the
cause measurably is, and how to generate a fix tailored to your own usage.

The research is a case study: **93,994 real assistant turns across 280 sessions**
(28 Jun – 9 Sep 2026), parsed from local Claude Code transcripts. No estimates,
no vendor marketing — every counterfactual is a re-priced replay of actual
history. The mechanism generalizes; the specific numbers won't be yours, which is
why the [instructions are generated from your own data](#automating-it--generate-instructions-from-your-usage)
rather than copied.

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
instructions/              Generator prompt + templates (see below)
tools/analyze_usage.py     Re-measurable analyzer — run it yourself
data/                      Baseline snapshots for before/after comparison
```

## Automating it — generate instructions from *your* usage

Token waste has a shape, and yours won't match the profile above. Someone
burning 1M-token marathon sessions needs different rules from someone running
hundreds of small sessions on an overpriced model. So rather than copying a
fixed instruction block, generate your own:

> **[instructions/GENERATE-MY-INSTRUCTIONS.md](instructions/GENERATE-MY-INSTRUCTIONS.md)**
> — a prompt you paste into Claude Code. It measures your transcripts, diagnoses
> which of eight token problems you actually have, and writes a paste-ready
> block containing **only** the rules your numbers justify. Drop the result into
> **Settings → Instructions for Claude**.

Also in [`instructions/`](instructions/):

- [`CLAUDE.md.template`](instructions/CLAUDE.md.template) — copy into any repo as
  `CLAUDE.md` for project-specific trimmed commands and conventions.
- [`claude-user-instructions.md`](instructions/claude-user-instructions.md) —
  generic baseline template if you can't run the analyzer.
- [`examples/heavy-opus-marathon-user.md`](instructions/examples/heavy-opus-marathon-user.md)
  — the generator prompt run end-to-end on the 93,994-turn profile above.

> **Two constraints every template here encodes.** Claude cannot change its own
> model or effort — those are your controls, so instructions can only make it
> *flag* a mismatch. And changing model or effort *mid-conversation* invalidates
> the prompt cache, re-billing the whole context at ~12.5× the read rate — so
> routing is **per session**, never per turn. See
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
