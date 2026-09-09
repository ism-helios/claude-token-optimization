# Cost model — how usage is actually metered

## The plan

Claude paid plans meter two ways simultaneously:

- **Session limit** — a rolling 5-hour window
- **Weekly limit** — resets 7 days after it first started filling, at a fixed
  time assigned to the account

Claude Code, the web app, desktop, and mobile all draw from **one shared pool**.
There is no separate Claude Code allowance. Every prompt, tool call, file read
and thinking block counts.

Metering is weighted, not a flat message count:

- Output tokens cost roughly **5× input** tokens
- Larger models cost proportionally more
- **Cached reads cost ~0.1× fresh input**
- On subscriptions the cache TTL is **1 hour** (5 minutes on API keys)

That last pair is the whole game.

## Published rates

$ per million tokens. Cache read ≈ 0.1× input; cache write ≈ 1.25× input.

| Model | Input | Output | Cache read | Cache write |
| ----- | ----- | ------ | ---------- | ----------- |
| Fable 5.1 | $10.00 | $50.00 | **$0.25** | $12.50 |
| Fable 5 | $10.00 | $50.00 | **$1.00** | $12.50 |
| Opus 5 | $5.00 | $25.00 | $0.50 | $6.25 |
| Opus 4.8 | $5.00 | $25.00 | $0.50 | $6.25 |
| Sonnet 5 | $2.00 | $10.00 | $0.20 | $2.50 |
| Haiku 4.5 | $1.00 | $5.00 | $0.10 | $1.25 |

Notes:

- **Fable is the premium tier, above Opus** — 2× Opus 5 per token. It is not a
  "newer Opus"; it is a more expensive class. Reach for it deliberately.
- **Fable 5 → Fable 5.1 is free money** if you need that tier: identical price
  per token, but 4× cheaper cache reads. Since cache reads are ~65% of real
  consumption, this is a large practical difference.
- Haiku 4.5 has a 200K context window; everything else above is 1M.

## Why cache reads dominate

Claude Code resends the whole conversation on every turn. Turn *n* pays for all
context accumulated through turn *n−1*.

Total consumption for a session of `N` turns with context growing to `C`:

```
cost  ≈  Σ(turn 1..N) context(turn) × cache_read_rate
      ≈  N × (C/2) × rate          # for roughly linear growth
```

Cost is **quadratic in session length**: doubling the turns at the same growth
rate quadruples consumption. This is why the measured cost per turn was
`$0.099` in short sessions and `$0.405` in 1000+ turn sessions.

A worked example on Opus 5 at $0.50/MTok cache read:

| Context | Cost of one turn (cache read alone) |
| ------- | ----------------------------------- |
| 50K | $0.025 |
| 200K | $0.10 |
| 500K | $0.25 |
| 1M | **$0.50** |

At a 1M context, *every single turn* — including "yes", "run the tests", and
"looks good" — costs $0.50 before Claude generates anything. A 2,000-turn
session at that size is ~$1,000 of pure re-reading.

## What invalidates the cache

Cache matching is **prefix-based**: any byte change invalidates everything after
it. Render order is `tools` → `system` → `messages`.

Invalidating the prefix means the entire context is re-billed at **cache write**
price (1.25× input, i.e. **12.5× the cache-read rate**) instead of 0.1×.

Things that invalidate it:

| Action | Effect |
| ------ | ------ |
| **Changing model mid-conversation** | Full re-write of context |
| **Changing effort mid-conversation** | Full re-write of context |
| Enabling/disabling an MCP server | Changes the tool list → full re-write |
| Editing `CLAUDE.md` mid-session | Changes system prefix → full re-write |
| >1 hour idle | Cache expires → next turn is a full re-write |

**Consequence for routing:** switching from Sonnet to Opus at turn 400 of a
600K-token session costs more than the entire preceding session. Route
**per session**, never per turn. This is the single most important operational
detail in this repo.

## Reading the numbers in this repo

The dollar figures throughout are **API list-price equivalents** derived from
transcript token counts. They are not a bill — a Max plan is flat-rate. They are
a proxy for the weighted metering above, which is what makes the ratios and the
counterfactual replays meaningful.

Verify any of it with:

```bash
python3 tools/analyze_usage.py
```
