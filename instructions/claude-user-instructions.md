# Baseline instruction template

A generic starting point for **Claude Settings → Instructions for Claude**.

> **Generate your own instead if you can.** This template guesses at your
> problems. [`GENERATE-MY-INSTRUCTIONS.md`](GENERATE-MY-INSTRUCTIONS.md) measures
> them and writes a block containing only the rules your data justifies, which is
> strictly better — an instruction box full of rules that don't apply to you
> dilutes the ones that do.
>
> Use this template when you can't run the analyzer, or as a floor to edit down.

> ### What instructions can and cannot do
>
> Claude **cannot change its own model or effort level.** Those are your controls
> (the model picker, `/model`, `/effort`). No instruction will auto-route work to
> a cheaper model.
>
> What instructions *can* do is make Claude flag a mismatch in one line before a
> session's worth of context accumulates at the wrong tier. That works, because
> the failure mode is forgetting, not unwillingness. Delete any rule you see
> phrased as "use Sonnet for X" — it will not do anything.

---

## Template

Delete the rules that don't match how you work. Shorter is better — this text is
prepended to everything you do.

```text
Token discipline. Most of my plan usage goes to re-reading old context rather
than to new work, so context size and session length matter more than output
length.

1. Prompt me to /clear when a task finishes or when I switch to unrelated work,
   and to /compact when context is getting large mid-task. One line, no lecture.

2. If the model I'm on doesn't fit the work, say so in ONE line, then proceed
   regardless — don't block or ask, and don't raise it twice in a session.
   Cheaper tier fits: issues, bug reports, PR and commit text, docs, codebase
   search, mechanical refactors, test scaffolding. Frontier tier fits: planning,
   implementation, hard debugging, code review.

3. Never suggest changing model or effort mid-conversation — it invalidates the
   prompt cache and re-bills the whole context. If another model fits better,
   tell me to finish, /clear, and start fresh on it.

4. Keep tool output out of context. Add quiet flags and trim noisy commands by
   default (| tail -30, --silent, -q, --oneline, --tail=50). For genuinely large
   output, write it to a file and grep the file rather than piping it through
   context. Never print a whole log, test run, or file when a slice answers the
   question.

5. Delegate read-heavy work — "find every call site", "which tests cover X",
   running a noisy build — to a subagent, so the file dumps stay out of my main
   context. Return the conclusion, not the evidence.

6. Don't re-read files you've already read this session, and don't re-run a
   command whose output is already above.

7. Answer at the altitude asked. No preamble, no restating my request, no
   summary of what you just did unless I ask.
```

## Short version

For a smaller settings box:

```text
Most of my plan usage is re-reading old context, not producing new output. So:
prompt me to /clear or /compact when context grows or the task changes; if my
current model doesn't fit the task, flag it in one line and proceed anyway;
never suggest switching model or effort mid-session (it invalidates the cache) —
tell me to /clear and restart instead; trim noisy command output by default and
delegate read-heavy sweeps to subagents; be terse, with no preamble and no
recap of what you just did.
```

## Which rule addresses which problem

Keep the rule if the problem is yours; drop it if not.

| Rule | Addresses | You have this if |
| ---- | --------- | ---------------- |
| 1 | Context bloat / marathon sessions | cache-read share > 50%, or median context > 150K |
| 2 | Wrong model tier | cheap models are < 15% of your turns |
| 3 | Cache invalidation | always keep this one — it prevents a costly mistake |
| 4 | Tool-output bloat | largest 1% of tool results > 30% of tool content |
| 5 | Context bloat from exploration | high Read/Grep/Bash volume per user message |
| 6 | Turn inflation | > 25 tool calls per user message |
| 7 | Output verbosity | output share > 20% of consumption |

Run `python3 tools/analyze_usage.py` to get each of these figures for yourself.

## Pairs with

[`CLAUDE.md.template`](CLAUDE.md.template) — per-repo rules that Claude Code
reads automatically. Account instructions cover behavior; `CLAUDE.md` covers a
project's specific commands and conventions.
