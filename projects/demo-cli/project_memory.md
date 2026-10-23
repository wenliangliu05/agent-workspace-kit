# Log triage CLI (demo)

## Goal

Point it at a 1-2 GB log file and get "which lines matter" in under ten
seconds: group by normalized pattern, sort by count, show the first sample.

## State

- status: paused (waiting on a real log to tune the normalizer)
- last touched: 2026-10-05
- working: streaming parse, pattern normalization, `--top N`
- not started: time-window filters, JSON output

## Key files

| Path | Why it matters |
| --- | --- |
| `triage.py` | the whole tool, ~200 lines |
| `samples/` | small, sanitized log snippets for tests |

## Gotchas

- Never `read()` the file. Everything is a generator; the 2 GB case is the
  normal case here, and a "just this once" full read has OOM'd twice.
- Timestamps come in three formats (ISO, syslog, epoch). Normalize before
  counting, or the same event splits into three buckets.
- Counts are approximate by design. Do not add a global `Counter` "just to be
  exact" - that is what broke the memory ceiling.

## Skills

- `debugging` - for pattern-normalization bugs

## Next steps

- [ ] split the normalizer into pure functions so it can be unit-tested
- [ ] add `--since 1h` (needs the timestamp normalizer first)
- [ ] sample a real log, keep 20 lines, add to `samples/`
