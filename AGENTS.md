# AGENTS.md

Read this before touching anything in this workspace. It is short on purpose.

## What this workspace is

A workspace is **one JSON index plus one handoff pack per project**:

```
_index.json                        # the single source of truth
projects/<id>/project_memory.md    # the handoff pack for that project
skills/<name>/SKILL.md             # optional, loaded on demand
assets/tools/ws.py                 # the only CLI you need
```

## Rules

1. **Ask the index, don't crawl the disk.**
   Do not use `ls`, `tree`, `find`, or `grep` to discover projects or their
   state. Use:

   ```bash
   python3 assets/tools/ws.py list                 # what exists
   python3 assets/tools/ws.py find <keyword>       # where is it
   python3 assets/tools/ws.py handoff <id>         # what do I need to know
   ```

2. **Read the pack before editing.**
   `handoff <id>` prints: goal, state, key files, gotchas, skills, next steps.
   If a gotcha contradicts your plan, the gotcha wins until you prove otherwise.

3. **Persist ⇒ project.**
   If something must survive this session (a decision, a fix, a path), it goes
   into the project's pack or into a new project. A file dropped in the root is
   a file nobody will find again.

4. **Update the pack before you finish.**
   - `## State`: what is true now (not what you intended)
   - `## Next steps`: the next concrete task, as a checkbox list
   - `## Gotchas`: anything that cost you more than ten minutes
   - bump `updated` in `_index.json` (or let `ws.py check --fix` remind you)

5. **Write non-inferable things only.**
   The pack is not documentation. If a reader could derive it by reading the
   code in two minutes, it does not belong in the pack. Traps, rejected
   approaches, "the obvious fix breaks X" - those belong here.

6. **Keep a pack under ~60 lines.**
   A pack that grows into a design document stops being read. Move history to
   git, decisions to an ADR in the project, and leave the pack sharp.

7. **Never rename ids.**
   `id` is a stable slug (`demo-api`). Titles change, ids don't. Links, habits
   and the index all depend on this.

8. **One writer at a time.**
   The index is a plain JSON file. If two agents write concurrently, the last
   write wins. Serialise your updates (the CLI writes atomically enough for
   interactive use, not for parallel fan-out).

## Adding a project

```bash
python3 assets/tools/ws.py new "Invoice importer" --type backend \
    --stack python --stack sqlite --tag etl
# → creates projects/invoice-importer/{README.md,project_memory.md}
# → registers it in _index.json
```

Then fill in `project_memory.md`. A pack with a filled `## Goal` and
`## Gotchas` is already more useful than most READMEs.

## Skills

`skills/<name>/SKILL.md` holds a skill with YAML front-matter (`name`,
`description`). `handoff` lists the skills that match a project's `stack`/`tags`
and points at their paths. Load a skill only when its description matches the
task - that is the whole point of keeping them out of the prompt.

## Checking your work

```bash
python3 assets/tools/ws.py check   # index <-> disk consistency
make lint                          # ruff (if installed)
make test                          # the CLI's own tests
```
