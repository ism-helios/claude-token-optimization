#!/usr/bin/env python3
"""
Analyze local Claude Code transcripts to find where plan usage actually goes.

Reads ~/.claude/projects/**/*.jsonl (never leaves your machine, never sends data
anywhere) and reports the drivers of token consumption: context size per request,
session length, model mix, and tool-result bloat.

Usage:
    python3 tools/analyze_usage.py                       # full report, last 90 days
    python3 tools/analyze_usage.py --days 7              # just this week
    python3 tools/analyze_usage.py --json data/base.json # machine-readable snapshot
    python3 tools/analyze_usage.py --compare data/base.json   # did we improve?

Dollar figures are API list-price equivalents. They are NOT your bill (you pay a
flat subscription). They are a proxy for how the plan meters usage, which is what
makes the ratios and the counterfactuals meaningful.
"""

import argparse
import collections
import datetime as dt
import glob
import json
import os
import statistics
import sys

# $ per million tokens: (input, output, cache_read, cache_write)
# Keep in sync with docs/02-cost-model.md
PRICES = {
    "claude-opus-5":              (5.0,  25.0, 0.50,  6.25),
    "claude-opus-4-8":            (5.0,  25.0, 0.50,  6.25),
    "claude-opus-4-7":            (5.0,  25.0, 0.50,  6.25),
    "claude-fable-5":             (10.0, 50.0, 1.00, 12.50),
    "claude-fable-5-1":           (10.0, 50.0, 0.25, 12.50),
    "claude-sonnet-5":            (2.0,  10.0, 0.20,  2.50),
    "claude-sonnet-4-6":          (3.0,  15.0, 0.30,  3.75),
    "claude-haiku-4-5-20251001":  (1.0,   5.0, 0.10,  1.25),
    "claude-haiku-4-5":           (1.0,   5.0, 0.10,  1.25),
}
DEFAULT_PRICE = (5.0, 25.0, 0.50, 6.25)  # assume Opus-tier for unknown models

TRANSCRIPTS = os.path.expanduser("~/.claude/projects")


# ----------------------------------------------------------------- loading

def load(days=90, root=TRANSCRIPTS):
    """Return (turns, tool_calls, tool_result_sizes) parsed from transcripts."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    turns, tool_calls, tool_results = [], collections.Counter(), []
    files = glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)
    if not files:
        sys.exit(f"No transcripts found under {root}")

    for path in files:
        project = os.path.basename(os.path.dirname(path))
        session = os.path.basename(path)[:-6]
        for line in open(path, errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue

            ts = rec.get("timestamp", "")
            if ts:
                try:
                    if dt.datetime.fromisoformat(ts.replace("Z", "+00:00")) < cutoff:
                        continue
                except ValueError:
                    pass

            kind = rec.get("type")
            msg = rec.get("message") or {}
            content = msg.get("content")

            if kind == "assistant":
                usage = msg.get("usage") or {}
                if usage:
                    turns.append({
                        "project": project, "session": session, "ts": ts,
                        "model": msg.get("model", "?"),
                        "sidechain": bool(rec.get("isSidechain")),
                        "effort": rec.get("effort") or "(unset)",
                        "input": usage.get("input_tokens") or 0,
                        "cache_write": usage.get("cache_creation_input_tokens") or 0,
                        "cache_read": usage.get("cache_read_input_tokens") or 0,
                        "output": usage.get("output_tokens") or 0,
                        "thinking": (usage.get("output_tokens_details") or {}).get("thinking_tokens") or 0,
                    })
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_calls[block.get("name", "?")] += 1

            elif kind == "user" and isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_results.append(len(json.dumps(block.get("content", ""))))

    return turns, tool_calls, tool_results


# ----------------------------------------------------------------- costing

def cost(turn, model=None, context_cap=None):
    """API-list-price equivalent for one turn, optionally re-simulated."""
    inp, out, cr, cw = PRICES.get(model or turn["model"], DEFAULT_PRICE)
    cache_read = turn["cache_read"]
    if context_cap:
        fixed = turn["input"] + turn["cache_write"]
        if fixed + cache_read > context_cap:
            cache_read = max(0, context_cap - fixed)
    return (turn["input"] * inp + turn["output"] * out
            + cache_read * cr + turn["cache_write"] * cw) / 1e6


def context_size(turn):
    return turn["input"] + turn["cache_write"] + turn["cache_read"]


def simulate(turns, context_cap=None, swap_to=None, swap_fraction=0.0):
    """Re-price history under different habits. Deterministic sampling so runs
    are reproducible."""
    total = 0.0
    for turn in turns:
        model = None
        if swap_to and turn["model"].startswith(("claude-opus", "claude-fable")):
            seed = hash(turn["session"] + turn["ts"]) % 1000
            if seed / 1000 < swap_fraction:
                model = swap_to
        total += cost(turn, model=model, context_cap=context_cap)
    return total


# ----------------------------------------------------------------- reporting

def pct(part, whole):
    return 100 * part / whole if whole else 0.0


def build_report(turns, tool_calls, tool_results):
    total = sum(cost(t) for t in turns)
    stamps = sorted(t["ts"] for t in turns if t["ts"])
    span_days = 1
    if len(stamps) > 1:
        first = dt.datetime.fromisoformat(stamps[0].replace("Z", "+00:00"))
        last = dt.datetime.fromisoformat(stamps[-1].replace("Z", "+00:00"))
        span_days = max(1, (last - first).days + 1)

    # component split
    components = collections.Counter()
    for t in turns:
        inp, out, cr, cw = PRICES.get(t["model"], DEFAULT_PRICE)
        components["cache_read"] += t["cache_read"] * cr / 1e6
        components["cache_write"] += t["cache_write"] * cw / 1e6
        components["output"] += t["output"] * out / 1e6
        components["input"] += t["input"] * inp / 1e6

    # per model
    by_model = collections.Counter()
    model_turns = collections.Counter()
    for t in turns:
        by_model[t["model"]] += cost(t)
        model_turns[t["model"]] += 1

    # per session
    sessions = collections.defaultdict(lambda: {"cost": 0.0, "turns": 0, "peak_context": 0})
    for t in turns:
        s = sessions[(t["project"], t["session"])]
        s["cost"] += cost(t)
        s["turns"] += 1
        s["peak_context"] = max(s["peak_context"], context_size(t))

    buckets = collections.defaultdict(lambda: {"sessions": 0, "cost": 0.0, "turns": 0})
    for s in sessions.values():
        n = s["turns"]
        key = ("1-50" if n <= 50 else "51-200" if n <= 200 else
               "201-500" if n <= 500 else "501-1000" if n <= 1000 else "1000+")
        buckets[key]["sessions"] += 1
        buckets[key]["cost"] += s["cost"]
        buckets[key]["turns"] += n

    contexts = sorted(context_size(t) for t in turns if context_size(t) > 0)
    ctx_total = sum(contexts)

    return {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "span_days": span_days,
        "window": [stamps[0][:10], stamps[-1][:10]] if stamps else [],
        "turns": len(turns),
        "sessions": len(sessions),
        "total_usd_equiv": round(total, 2),
        "weekly_usd_equiv": round(total / span_days * 7, 2),
        "components_pct": {k: round(pct(v, total), 1) for k, v in components.items()},
        "by_model": {
            m: {"pct": round(pct(v, total), 1), "turns": model_turns[m]}
            for m, v in by_model.most_common()
        },
        "context": {
            "median": contexts[len(contexts) // 2] if contexts else 0,
            "p90": contexts[int(len(contexts) * 0.9)] if contexts else 0,
            "max": contexts[-1] if contexts else 0,
            "pct_tokens_above_500k": round(
                pct(sum(c for c in contexts if c > 500_000), ctx_total), 1),
        },
        "session_buckets": {
            k: {"sessions": v["sessions"], "pct_of_cost": round(pct(v["cost"], total), 1),
                "usd_per_turn": round(v["cost"] / v["turns"], 4) if v["turns"] else 0}
            for k, v in sorted(buckets.items())
        },
        "marathon_pct": round(
            pct(sum(s["cost"] for s in sessions.values() if s["turns"] > 1000), total), 1),
        "tool_calls": dict(tool_calls.most_common(15)),
        "tool_calls_total": sum(tool_calls.values()),
        "tool_result_top1pct_share": round(
            pct(sum(sorted(tool_results)[int(len(tool_results) * 0.99):]),
                sum(tool_results)), 1) if tool_results else 0,
        "levers": {
            "cap_500k": round(100 - pct(simulate(turns, context_cap=500_000), total), 1),
            "cap_300k": round(100 - pct(simulate(turns, context_cap=300_000), total), 1),
            "cap_200k": round(100 - pct(simulate(turns, context_cap=200_000), total), 1),
            "cap_120k": round(100 - pct(simulate(turns, context_cap=120_000), total), 1),
            "sonnet_40pct": round(
                100 - pct(simulate(turns, swap_to="claude-sonnet-5", swap_fraction=0.4), total), 1),
            "cap200k_plus_sonnet40": round(
                100 - pct(simulate(turns, context_cap=200_000, swap_to="claude-sonnet-5",
                                   swap_fraction=0.4), total), 1),
            "cap120k_plus_sonnet50": round(
                100 - pct(simulate(turns, context_cap=120_000, swap_to="claude-sonnet-5",
                                   swap_fraction=0.5), total), 1),
        },
    }


def print_report(r):
    w = r["window"]
    print(f"\n{'=' * 68}")
    print(f"  CLAUDE USAGE PROFILE   {w[0] if w else '?'} -> {w[-1] if w else '?'}"
          f"   ({r['span_days']} days)")
    print(f"{'=' * 68}")
    print(f"  {r['turns']:,} turns across {r['sessions']:,} sessions")
    print(f"  ${r['total_usd_equiv']:,.0f} API-list-price equivalent"
          f"  (~${r['weekly_usd_equiv']:,.0f}/week)")

    print("\n  WHERE IT GOES")
    labels = {"cache_read": "cache reads (re-sending old context)",
              "cache_write": "cache writes (loading new context)",
              "output": "output (answers + thinking)",
              "input": "fresh input"}
    for k, v in sorted(r["components_pct"].items(), key=lambda x: -x[1]):
        print(f"    {labels.get(k, k):42} {v:5.1f}%")

    print("\n  MODEL MIX")
    for m, d in r["by_model"].items():
        print(f"    {m:28} {d['pct']:5.1f}%   {d['turns']:,} turns")

    c = r["context"]
    print("\n  CONTEXT PER REQUEST")
    print(f"    median {c['median']:,}   p90 {c['p90']:,}   max {c['max']:,}")
    print(f"    {c['pct_tokens_above_500k']}% of tokens spent above 500K context")

    print("\n  SESSION LENGTH vs COST")
    for k in ("1-50", "51-200", "201-500", "501-1000", "1000+"):
        if k in r["session_buckets"]:
            b = r["session_buckets"][k]
            print(f"    {k:9} {b['sessions']:4} sessions  {b['pct_of_cost']:5.1f}% of cost"
                  f"   ${b['usd_per_turn']:.3f}/turn")
    print(f"    sessions over 1000 turns = {r['marathon_pct']}% of everything")

    print("\n  TOOL BLOAT")
    print(f"    {r['tool_calls_total']:,} tool calls; top 3: "
          + ", ".join(f"{k} ({v:,})" for k, v in list(r["tool_calls"].items())[:3]))
    print(f"    largest 1% of tool results = {r['tool_result_top1pct_share']}%"
          f" of all tool-result content")

    print("\n  PROJECTED SAVINGS (same work, different habits)")
    names = {
        "cap_500k": "clear/compact at ~500K context",
        "cap_300k": "clear/compact at ~300K context",
        "cap_200k": "clear/compact at ~200K context",
        "cap_120k": "clear/compact at ~120K context",
        "sonnet_40pct": "route 40% of turns to Sonnet 5",
        "cap200k_plus_sonnet40": "200K cap + 40% Sonnet  [recommended]",
        "cap120k_plus_sonnet50": "120K cap + 50% Sonnet  [aggressive]",
    }
    for k, v in r["levers"].items():
        print(f"    {names.get(k, k):42} -{v:5.1f}%")
    print()


def compare(baseline, current):
    print(f"\n{'=' * 68}")
    print("  COMPARISON vs BASELINE")
    print(f"{'=' * 68}")
    print(f"  baseline: {baseline['window'][0]} -> {baseline['window'][-1]}"
          f"  (${baseline['weekly_usd_equiv']:,.0f}/wk)")
    print(f"  current:  {current['window'][0]} -> {current['window'][-1]}"
          f"  (${current['weekly_usd_equiv']:,.0f}/wk)")
    delta = pct(current["weekly_usd_equiv"] - baseline["weekly_usd_equiv"],
                baseline["weekly_usd_equiv"])
    verdict = "IMPROVED" if delta < -5 else "REGRESSED" if delta > 5 else "FLAT"
    print(f"\n  weekly burn: {delta:+.1f}%   ->  {verdict}")

    rows = [
        ("median context", "context", "median", "{:,}"),
        ("% tokens above 500K ctx", "context", "pct_tokens_above_500k", "{}%"),
        ("marathon sessions share", None, "marathon_pct", "{}%"),
        ("cache-read share", "components_pct", "cache_read", "{}%"),
    ]
    print(f"\n  {'metric':30} {'baseline':>14} {'current':>14}")
    for label, section, key, fmt in rows:
        b = baseline[section][key] if section else baseline[key]
        c = current[section][key] if section else current[key]
        print(f"  {label:30} {fmt.format(b):>14} {fmt.format(c):>14}")

    print(f"\n  {'model':28} {'baseline':>10} {'current':>10}")
    for m in sorted(set(baseline["by_model"]) | set(current["by_model"])):
        b = baseline["by_model"].get(m, {}).get("pct", 0)
        c = current["by_model"].get(m, {}).get("pct", 0)
        print(f"  {m:28} {b:9.1f}% {c:9.1f}%")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=90, help="lookback window (default 90)")
    ap.add_argument("--json", metavar="PATH", help="write a snapshot for later comparison")
    ap.add_argument("--compare", metavar="PATH", help="diff current usage against a snapshot")
    ap.add_argument("--root", default=TRANSCRIPTS, help="transcript directory")
    ap.add_argument("--quiet", action="store_true", help="suppress the text report")
    args = ap.parse_args()

    report = build_report(*load(days=args.days, root=args.root))

    if not args.quiet:
        print_report(report)

    if args.compare:
        with open(args.compare) as fh:
            compare(json.load(fh), report)

    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        with open(args.json, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"snapshot written to {args.json}")


if __name__ == "__main__":
    main()
