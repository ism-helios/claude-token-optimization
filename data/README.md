# Snapshots

JSON snapshots from `tools/analyze_usage.py --json`, used for before/after
comparison.

- `baseline-2026-09-09.json` — the original measurement, before any changes.
  Do not overwrite this one; it's the reference point.

Capture a new one weekly:

```bash
python3 tools/analyze_usage.py --days 7 --json data/week-$(date +%V).json
python3 tools/analyze_usage.py --days 7 --compare data/baseline-2026-09-09.json
```

Snapshots contain aggregate token counts and project *folder names* only — no
code, prompts, or conversation content.
