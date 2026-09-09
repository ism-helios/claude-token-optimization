# Instructions

Turning the research into something that applies without you remembering it.

## Start here

**[GENERATE-MY-INSTRUCTIONS.md](GENERATE-MY-INSTRUCTIONS.md)** — a prompt you
paste into Claude Code. It measures your own transcripts, diagnoses which token
problems you actually have, and writes an instruction block containing only the
rules your data justifies.

This is the recommended path. Token waste has a shape, and yours won't match
anyone else's — someone burning 1M-token marathon sessions needs different rules
from someone running hundreds of small sessions on an overpriced model.

## The rest

| File | What it's for |
| ---- | ------------- |
| [`GENERATE-MY-INSTRUCTIONS.md`](GENERATE-MY-INSTRUCTIONS.md) | The prompt. Generates personalized instructions from your usage. |
| [`claude-user-instructions.md`](claude-user-instructions.md) | Generic baseline template, if you can't run the analyzer. Weaker — it guesses at your problems. |
| [`CLAUDE.md.template`](CLAUDE.md.template) | Per-repo file Claude Code reads automatically. Encodes your project's trimmed commands and conventions. |
| [`examples/heavy-opus-marathon-user.md`](examples/heavy-opus-marathon-user.md) | The generator prompt run end-to-end on a real 93,994-turn profile. |

## Two layers, different jobs

- **Account instructions** (Settings → Instructions for Claude) — behavior that
  should hold everywhere: session hygiene, model-mismatch flagging, terseness.
- **`CLAUDE.md`** (per repo) — project specifics: which commands to run, with
  which output flags, what not to touch.

Use both. They don't overlap.

## The one hard constraint

**Claude cannot change its own model or effort level.** Those are your controls
(model picker, `/model`, `/effort`). No instruction file auto-routes work to a
cheaper model.

What instructions *can* do is get Claude to flag a mismatch in one line before a
session's worth of context piles up at the wrong tier — which works, because the
failure mode is forgetting, not unwillingness.

And the corollary that costs people money: **never switch model or effort
mid-conversation.** It invalidates the prompt cache and re-bills the entire
accumulated context at cache-write price, roughly 12.5× the read rate. Finish,
`/clear`, then restart on the other model. Every template here encodes that.
