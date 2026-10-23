# Contributing

Thanks for looking. This is a small tool with a deliberately small surface, so
the best contributions are usually a sharper gotcha, a new test, or a bug in the
CLI — not a new feature.

## Ground rules

1. **Standard library only.** The CLI must run on a bare container with no
   network and no `pip install`. Build tools (ruff) are development-only.
2. **One file for the CLI.** `assets/tools/ws.py` stays a single module; it is
   packaged as a module and copied into new workspaces, so splitting it would
   break `init`.
3. **Behaviour changes come with tests.** `tests/test_ws.py` drives the CLI as a
   subprocess, the way an agent would. Add a test that fails before your change.
4. **Keep the packs short.** If a change makes `project_memory.md` files longer,
   it is probably going in the wrong place.
5. **100 columns, Python 3.10 syntax.** `pyproject.toml` encodes both.

## Development loop

```bash
git clone https://github.com/wenliangliu05/agent-workspace-kit
cd agent-workspace-kit

make check    # index <-> disk consistency (no dependencies)
make test     # 20 tests (no dependencies)
make lint     # ruff (pip install ruff)

python3 assets/tools/ws.py handoff demo-api   # the thing users see
```

Want to try the packaging path as well?

```bash
python3 -m venv /tmp/ws && /tmp/ws/bin/pip install .
/tmp/ws/bin/ws handoff demo-api
```

## Pull requests

- One concern per PR. Small is fast.
- Subject line: imperative, ≤ 72 chars. Chinese or English is fine; the body
  should explain *why*, not restate the diff.
- If you change user-visible behaviour, add a line under `## [Unreleased]` in
  `CHANGELOG.md`.
- CI must be green: lint, tests, `check`, and the end-to-end smoke test all run
  on 3.10 / 3.11 / 3.13 and on Windows.

## Where things live

| Path | Meaning |
| --- | --- |
| `assets/tools/ws.py` | the whole CLI (packaged as module `ws`) |
| `_index.json` | the index the CLI reads and writes |
| `projects/demo-*/project_memory.md` | example handoff packs — good models to copy |
| `skills/debugging/SKILL.md` | example skill (progressive disclosure) |
| `tests/test_ws.py` | the suite you must keep green |
| `AGENTS.md` | the rules agents follow inside a workspace |

## Reporting a bug

Include: the command you ran, the exit code, and the relevant part of
`_index.json` / `project_memory.md` with anything private removed. `ws check`
output is usually enough to see what went out of sync.
