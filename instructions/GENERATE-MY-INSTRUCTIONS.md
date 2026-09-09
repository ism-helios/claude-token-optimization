# Generate your own Claude instructions

Your token usage has a shape. Someone whose problem is 1M-token marathon
sessions needs different rules from someone running hundreds of small sessions
on an expensive model. Generic advice wastes half the instruction box on rules
that don't apply to you.

So don't copy someone else's instructions. **Generate your own from your own
data.**

---

## How to use this

1. Clone this repo (or just have `tools/analyze_usage.py` on disk).
2. Open Claude Code in the repo directory.
3. Paste the prompt below.
4. It runs the analyzer on your local transcripts and hands you a paste-ready
   instruction block containing **only** the rules your numbers justify.
5. Paste that into **Claude Settings → Instructions for Claude**.

Nothing is uploaded. The analyzer reads `~/.claude/projects/**/*.jsonl` locally
and reports aggregate token counts only.

---

## The prompt

Copy everything inside the block:

````text
Analyze my Claude Code token usage and write me a personalized "Instructions for
Claude" block that targets my actual waste.

STEP 1 — MEASURE
Run: python3 tools/analyze_usage.py --days 30 --json data/my-profile.json
(If that script isn't present, parse ~/.claude/projects/**/*.jsonl yourself: each
assistant record has message.usage with input_tokens, cache_creation_input_tokens,
cache_read_input_tokens, output_tokens, and message.model. Aggregate the same
metrics listed in Step 2.)

Show me the report before continuing.

STEP 2 — DIAGNOSE
From the numbers, state which of these problems I actually have, with the
supporting figure for each. Be honest — say "not a problem for you" where the
data says so. Do not assume my profile matches anyone else's.

  A. Context bloat        — cache-read share > 50%, or median context > 150K
  B. Marathon sessions    — sessions over 500 turns are > 25% of cost
  C. Wrong model tier     — cheap models (Sonnet/Haiku) < 15% of turns
  D. Overpriced tier      — any Fable-tier usage, or Fable 5 specifically
  E. Tool-output bloat    — largest 1% of tool results > 30% of tool content
  F. Turn inflation       — more than ~25 tool calls per user message
  G. Output verbosity     — output share > 20% of total consumption
  H. Effort mismatch      — 'high' or above on > 80% of turns

STEP 3 — WRITE THE INSTRUCTIONS
Produce ONE paste-ready plain-text block for the Claude settings box.

Rules:
- Include a rule ONLY for problems Step 2 confirmed. Omit the rest entirely —
  an instruction box full of irrelevant rules dilutes the ones that matter.
- Order the rules by how much each problem costs me, biggest first.
- Open with one sentence of context so the rules have a reason ("~X% of my usage
  is <my actual biggest driver>").
- Keep it under 200 words. It gets prepended to everything I do, so it must be
  short.
- Write it as direct instructions to you, in plain text, no markdown headers.
- Every rule must be behavioral — something you can actually act on. Do NOT
  write rules telling you to change model or effort; you cannot do that. For
  model problems, the rule is that you FLAG a mismatch in one line and then
  proceed anyway, without blocking or asking.
- Never tell me to switch model or effort mid-conversation. That invalidates the
  prompt cache and re-bills the whole accumulated context at cache-write price
  (~12.5x the read rate). The correct advice is always: finish, /clear, restart
  on the other model.

STEP 4 — TELL ME WHAT ELSE TO DO
Separately from the block, list the changes that instructions cannot fix —
settings to change, MCP servers to disable, habits to build — ranked by the
saving each one measured in Step 1. Then give me the exact command to re-measure
in a week.
````

---

## What you get back

A block shaped like this — but with *your* problems in it, not these:

```text
Token discipline (~65% of my usage is re-reading old context, so context size
and session length are what matter most):

1. Prompt me to /clear when a task finishes or I switch to unrelated work, and
   to /compact when context passes ~200K mid-task. One line, no lecture.
2. If my current model doesn't fit the work, say so in one line and proceed
   anyway — don't block or ask. Sonnet for issues, docs, search and mechanical
   edits; Opus for planning, implementation, debugging, review.
3. Never suggest switching model or effort mid-conversation. Tell me to finish,
   /clear, and restart instead.
4. Trim noisy command output by default (| tail -30, --silent, -q). For large
   output, write to a file and grep it rather than piping it through context.
5. Delegate read-heavy sweeps to subagents so file dumps stay out of my main
   context. Return the conclusion, not the evidence.
6. Be terse: no preamble, no restating my request, no summary of what you just
   did unless I ask.
```

A different profile produces a different block. Someone with 300 short sessions
on Fable and no context problem gets rules 2 and 3 and nothing else.

---

## Baseline template

If you'd rather not run the analyzer, [`claude-user-instructions.md`](claude-user-instructions.md)
has a generic template covering the rules that apply to most heavy users. It is
strictly worse than generating your own — it can't know which of your problems
are real — but it's better than nothing.

## Worked example

[`examples/heavy-opus-marathon-user.md`](examples/heavy-opus-marathon-user.md) —
a real profile (93,994 turns) run through this prompt end to end, so you can see
what the diagnosis and output look like on actual data.
