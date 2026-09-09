# Findings

Research conducted 9 September 2026 against local Claude Code transcripts.

## Method

`~/.claude/projects/**/*.jsonl` holds a full record of every Claude Code turn,
including the exact `usage` block the API returned:

```json
"usage": {
  "input_tokens": 2,
  "cache_creation_input_tokens": 16329,
  "cache_read_input_tokens": 38376,
  "output_tokens": 646,
  "output_tokens_details": { "thinking_tokens": 245 }
}
```

Every assistant turn was parsed and re-priced at published API rates
(see [02-cost-model.md](02-cost-model.md)). Counterfactuals are *replays*: the
same turn sequence re-costed with one variable changed, not a model of behavior.

**Corpus:** 93,994 assistant turns · 280 sessions · 284 transcript files ·
924 MB · 28 Jun – 9 Sep 2026 (73 days) · all via the `claude-desktop` entrypoint.

**Limitation.** Replaying with a context cap assumes the *same work* gets done in
the same number of turns after a `/clear`. In practice a cleared session needs a
few turns to re-establish context, so realized savings will land somewhat below
the projections. It also cannot model quality differences from a model swap —
those need judgment, which is what [04-model-routing.md](04-model-routing.md)
supplies.

---

## 1. Consumption is dominated by re-reading

| Component | Share |
| --------- | ----- |
| Cache reads | 65.4% |
| Cache writes | 24.3% |
| Output (incl. thinking) | 10.3% |
| Fresh input | 0.0% |

Thinking tokens were 17,260,026 of 91,242,229 output tokens (19% of output) but
only **1.7% of total consumption**. Turning thinking off is not the lever.

## 2. Context per request is enormous

| Percentile | Context tokens |
| ---------- | -------------- |
| p10 | 88,189 |
| p25 | 153,097 |
| **p50** | **300,690** |
| p75 | 524,855 |
| p90 | 751,320 |
| p99 | 957,861 |
| max | 998,273 |

Share of all tokens consumed by requests above a given context size:

| Above | Requests | Share of tokens |
| ----- | -------- | --------------- |
| 100K | 87.3% | 97.6% |
| 200K | 65.8% | 88.8% |
| 300K | 50.1% | 78.1% |
| **500K** | **27.4%** | **53.3%** |

Over half of all consumption happens in requests carrying more than half a
million tokens of history.

## 3. A handful of sessions dominate

| Turns/session | Sessions | Share of cost | Cost per turn |
| ------------- | -------- | ------------- | ------------- |
| 1–50 | 78 | 0.7% | $0.099 |
| 51–200 | 102 | 3.3% | $0.098 |
| 201–500 | 42 | 7.2% | $0.162 |
| 501–1000 | 37 | 33.3% | $0.372 |
| **1000+** | **21** | **55.5%** | **$0.405** |

Twenty-one sessions out of 280 are the majority of the bill. The cost-per-turn
column is the mechanism: a turn in a marathon session costs **4× a turn in a
short one** for identical work, because it drags the whole history along.

Largest single sessions:

| Cost-rank | Turns | Peak context |
| --------- | ----- | ------------ |
| 1 | 3,722 | 998,273 |
| 2 | 3,812 | 996,434 |
| 3 | 3,702 | 998,201 |
| 4 | 2,127 | 997,112 |
| 5 | 2,218 | 966,593 |

Only **58 compaction events** were found across all 280 sessions — sessions were
essentially never reset.

The heaviest project (`helios-mockup-crm`) consumed 19.2B tokens across 63
sessions — an average of **305M tokens per session**. Parallel worktrees are not
themselves the problem (each is legitimately separate work), but each one riding
to a 1M context multiplies the effect: 30 worktrees × 1M context is 30M tokens
re-read per round of turns.

## 4. Cheap models were effectively unused

| Model | Share of cost | Turns | Rate (in/out per MTok) |
| ----- | ------------- | ----- | ---------------------- |
| Opus 5 | 51.0% | 60,367 | $5 / $25 |
| **Fable 5** | **36.5%** | 20,398 | **$10 / $50** |
| Fable 5.1 | 6.4% | 4,932 | $10 / $50 (cache read $0.25) |
| Opus 4.8 | 6.1% | 7,735 | $5 / $25 |
| Sonnet 5 | 0.0% | **96** | $2 / $10 |
| Haiku 4.5 | 0.0% | **416** | $1 / $5 |

512 of 93,994 turns (0.5%) used a cheap model.

Two separate problems here:

- **No downshifting.** Mechanical work ran on frontier models.
- **Fable 5 is the most expensive option available** — 2× Opus 5 per token, and
  its cache reads cost $1.00/MTok vs Fable 5.1's $0.25. It was over a third of
  total consumption. Moving those turns to Fable 5.1 alone saves 18.4%; moving
  them to Opus 5 saves 18.9%.

Effort was `high` on 88,386 of 93,994 turns (94%).

## 5. Tool results bloat context

52,809 tool calls against 3,048 user messages — **17.3 tool calls per user
message.**

| Tool | Calls |
| ---- | ----- |
| Bash | 35,829 |
| Edit | 5,679 |
| Read | 2,699 |
| Write | 2,057 |
| Browser (all) | ~3,700 |

Tool-result payload sizes:

| | Chars |
| --- | --- |
| median | 335 |
| p90 | 3,955 |
| p99 | 100,580 |
| max | 824,920 |

- Largest **1%** of tool results = **58.7%** of all tool-result content
- Largest **5%** = 81%

A few hundred untrimmed command outputs are responsible for most of the context
growth — and because they persist, each one is re-read on every subsequent turn
in that session. A single 825KB result in a 2,000-turn session is paid for
roughly 1,000 times.

`Bash` being 68% of tool calls makes output discipline (`| tail -30`, `--quiet`,
redirect-then-grep) the highest-leverage tooling change.

## 6. Weekly trajectory

| Week of | Cost-equivalent |
| ------- | --------------- |
| 22 Jun | $104 |
| 29 Jun | $200 |
| 6 Jul | $254 |
| 13 Jul | $673 |
| 20 Jul | $1,888 |
| 27 Jul | $2,066 |
| 3 Aug | $2,855 |
| 10 Aug | $6,530 |
| 17 Aug | $6,495 |
| 24 Aug | $1,139 |
| 31 Aug | $5,441 |
| 7 Sep | $2,444 (partial week) |

Consumption grew ~60× in ten weeks. The 24 Aug trough is consistent with a
limit being hit. Peak weeks cluster around $6,500 — roughly 140× the plan's
weekly face value.

## Conclusion

The plan is not undersized for the work. The work is being delivered in a shape
that costs 2–3× what it needs to. The mechanism is `cost ∝ context × turns`, and
both factors were allowed to grow without bound.

See [03-playbook.md](03-playbook.md) for the remedies and
[04-model-routing.md](04-model-routing.md) for the routing policy.
