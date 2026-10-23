# Order API (demo)

## Goal

Expose a minimal order API (list / create / cancel) so the demo has something
concrete to hand off. Success = one command starts it, and the pack below is
enough for a fresh agent to add the next endpoint without reading the code.

## State

- status: active, v0.3
- last touched: 2026-10-20
- working: `GET /orders`, `POST /orders`, `POST /orders/{id}/cancel`
- not started: pagination, auth, deploy

## Key files

| Path | Why it matters |
| --- | --- |
| `src/app.py` | routing + handlers, ~120 lines, no framework |
| `src/db.py` | SQLite access; every write goes through one helper |
| `tests/` | run with `python -m unittest discover -s tests` |

## Gotchas

- Handlers are synchronous on purpose. Do not "upgrade" to asyncio without
  moving the DB calls to a thread - it was tried in October and deadlocked.
- SQLite is opened in WAL mode with a single writer. Two processes writing
  concurrently will return `database is locked` within ~5 s.
- `POST /orders` validates *after* writing by design (keeps the happy path
  one pass). If you add validation, keep the error shape identical.

## Skills

- `debugging` - for the "why is it locked" class of bug (see `skills/debugging`)
- (nothing else; this project is small on purpose)

## Next steps

- [ ] add `?limit=&offset=` to `GET /orders` with a default of 50
- [ ] decide auth: token in header vs. reverse proxy (write the decision here)
- [ ] add one test for the cancel path (currently only happy path is covered)
