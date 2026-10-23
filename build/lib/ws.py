#!/usr/bin/env python3
"""ws.py - the single entry point of an agent workspace.

Why a CLI instead of "just let the agent run ls/find/grep"?
-----------------------------------------------------------
Agents are good at reading, bad at *finding*. Every new session starts with
re-exploration: ls, tree, cat, grep, "where is that file again?". That costs
tokens and, worse, it costs the agent's attention.

This tool answers the three questions an agent actually asks, in one call:

    ws.py find <keyword>     where does this live?
    ws.py handoff <project>  what do I need to know before touching it?
    ws.py check              is the index still true?

Everything is one JSON file (`_index.json`) plus Markdown files on disk.
No database, no server, no dependencies - the standard library only.

Commands
--------
    init <dir>          create a new workspace skeleton
    new <slug>          create a project + its handoff pack, register it
    list                list projects (filter with --status / --type)
    find <keyword>      search id / title / tags / type / path
    show <id>           index entry + the top of its handoff pack
    handoff <id>        print the pack: memory, file map, skill pointers
    check               validate index <-> disk consistency (--fix to repair)

Exit codes: 0 ok, 1 validation problem, 2 usage error, 3 not found.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import NoReturn

__version__ = "0.2.0"

INDEX_NAME = "_index.json"
MEMORY_NAME = "project_memory.md"
PROJECTS_DIR = "projects"
SKILLS_DIR = "skills"
INDEX_VERSION = 1

# The six headings every handoff pack must have. Kept deliberately short: a
# pack that grows into a design document stops being read.
SECTIONS = ("Goal", "State", "Key files", "Gotchas", "Skills", "Next steps")

# Unicode-friendly: \w covers CJK, so `ws.py new "发票导入器"` works for
# non-English users while still forbidding path separators and dots.
SLUG_RE = re.compile(r"^\w[\w-]{0,47}$")

MEMORY_TEMPLATE = """# {title}

## Goal

{goal}

## State

- status: {status}
- last touched: {today}

## Key files

| Path | Why it matters |
| --- | --- |
| `README.md` | what this project is |
| `src/` | the code that matters |

## Gotchas

- (non-obvious facts only: rejected approaches, traps, "do not touch this")

## Skills

- (skills worth loading, e.g. `debugging` - see `skills/`)

## Next steps

- [ ] first concrete task
"""


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def today() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fail(message: str, code: int = 2) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def slugify(text: str) -> str:
    """Turn a human title into a stable, filesystem-safe id."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    return text.strip("-") or "project"


def find_root(start: Path | None = None, override: str | None = None) -> Path:
    """Locate the workspace root.

    Order: --root argument, WS_ROOT env var, then walk upwards looking for
    `_index.json`. Walking up (instead of assuming cwd) means the tool works
    from any subdirectory - which is how agents actually call it.
    """
    if override:
        root = Path(override).expanduser().resolve()
        if not (root / INDEX_NAME).is_file():
            fail(f"{root} is not a workspace (no {INDEX_NAME})", 2)
        return root
    env = os.environ.get("WS_ROOT")
    if env:
        root = Path(env).expanduser().resolve()
        if (root / INDEX_NAME).is_file():
            return root
    cur = (start or Path.cwd()).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / INDEX_NAME).is_file():
            return candidate
    fail(f"no {INDEX_NAME} found in {cur} or its parents; pass --root", 2)


def load_index(root: Path) -> dict:
    path = root / INDEX_NAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{INDEX_NAME} is not valid JSON: {exc}", 1)
    data.setdefault("schema_version", INDEX_VERSION)
    data.setdefault("projects", {})
    return data


def save_index(root: Path, index: dict) -> None:
    index["updated_at"] = now_iso()
    (root / INDEX_NAME).write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- #
# Handoff pack
# --------------------------------------------------------------------------- #

@dataclass
class Pack:
    project: str
    memory_path: Path | None
    missing_sections: list[str]

    @property
    def ok(self) -> bool:
        return self.memory_path is not None and not self.missing_sections


def read_memory(root: Path, entry: dict) -> Pack:
    rel = entry.get("memory") or f"{PROJECTS_DIR}/{entry['id']}/{MEMORY_NAME}"
    path = root / rel
    if not path.is_file():
        return Pack(entry["id"], None, list(SECTIONS))
    text = path.read_text(encoding="utf-8")
    missing = [name for name in SECTIONS
               if not re.search(rf"^##\s+{re.escape(name)}\s*$", text,
                                re.MULTILINE | re.IGNORECASE)]
    return Pack(entry["id"], path, missing)


def file_map(root: Path, entry: dict, depth: int = 2) -> list[str]:
    """Two levels of paths, not a full tree.

    A full tree is noise: architecture overviews did not measurably help agents
    locate files in the ETH study (arXiv 2602.11988), while non-inferable notes
    did. Depth 2 is enough to point at the right folder.
    """
    base = root / entry.get("path", f"{PROJECTS_DIR}/{entry['id']}")
    if not base.is_dir():
        return ["(missing on disk)"]
    lines: list[str] = []
    for child in sorted(base.iterdir()):
        if child.name in {".git", "__pycache__", "node_modules", ".venv"}:
            continue
        rel = child.relative_to(root).as_posix()
        lines.append(rel + ("/" if child.is_dir() else ""))
        if child.is_dir() and depth > 1:
            for sub in sorted(child.iterdir())[:12]:
                if sub.name in {".git", "__pycache__", "node_modules", ".venv"}:
                    continue
                lines.append("  " + sub.relative_to(root).as_posix()
                             + ("/" if sub.is_dir() else ""))
    return lines or ["(empty project)"]


def skill_pointers(root: Path, entry: dict) -> list[str]:
    skills_dir = root / SKILLS_DIR
    if not skills_dir.is_dir():
        return ["(no skills/ directory in this workspace)"]
    wanted = entry.get("stack", []) + entry.get("tags", [])
    names = [p.name for p in sorted(skills_dir.iterdir()) if p.is_dir()]
    if not names:
        return ["(skills/ is empty)"]
    hot = [n for n in names if any(w.lower() in n.lower() for w in wanted)]
    rest = [n for n in names if n not in hot]
    out = [f"{n}  ->  {SKILLS_DIR}/{n}/SKILL.md" for n in hot]
    if rest:
        out.append("others: " + ", ".join(rest))
    return out


def cmd_handoff(root: Path, index: dict, target: str, as_json: bool) -> int:
    entry = resolve(root, index, target)
    pack = read_memory(root, entry)
    skills = skill_pointers(root, entry)
    if as_json:
        print(json.dumps({
            "project": entry,
            "memory": pack.memory_path.read_text(encoding="utf-8") if pack.memory_path else None,
            "missing_sections": pack.missing_sections,
            "file_map": file_map(root, entry),
            "skills": skills,
        }, ensure_ascii=False, indent=2))
        return 0 if pack.ok else 1

    print(f"# handoff: {entry['id']}")
    print(f"# {entry.get('title', '')}  ({entry.get('status', '?')}, {entry.get('type', '?')})")
    print()
    print("== 1. project memory ==")
    if pack.memory_path:
        print(pack.memory_path.read_text(encoding="utf-8").strip())
    else:
        print(f"(missing: {entry.get('memory')})")
    if pack.missing_sections:
        print()
        print("   !! missing sections: " + ", ".join(pack.missing_sections))
    print()
    print("== 2. file map (depth 2) ==")
    for line in file_map(root, entry):
        print("  " + line)
    print()
    print("== 3. skills (load on demand) ==")
    for line in skills:
        print("  " + line)
    return 0 if pack.ok else 1


# --------------------------------------------------------------------------- #
# Index queries
# --------------------------------------------------------------------------- #

def resolve(root: Path, index: dict, target: str) -> dict:
    projects = index["projects"]
    if target in projects:
        return projects[target]
    hits = [p for pid, p in projects.items()
            if p.get("title", "").lower() == target.lower() or pid.startswith(target)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        fail(f"no project matches {target!r}; run `ws.py list`", 3)
    fail(f"{target!r} is ambiguous: " + ", ".join(p["id"] for p in hits), 2)


def cmd_list(root: Path, index: dict, status: str | None, ptype: str | None,
             as_json: bool) -> int:
    rows = [p for p in index["projects"].values()
            if (status is None or p.get("status") == status)
            and (ptype is None or p.get("type") == ptype)]
    rows.sort(key=lambda p: (p.get("status") != "active", p["id"]))
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("(no projects)")
        return 0
    width = max(len(p["id"]) for p in rows) + 2
    for p in rows:
        print(f"{p['id']:<{width}} {p.get('status', '?'):<8} {p.get('type', '?'):<12}"
              f" {p.get('title', '')}")
    return 0


def cmd_find(root: Path, index: dict, keyword: str, as_json: bool) -> int:
    needle = keyword.lower()
    hits = []
    for pid, p in index["projects"].items():
        haystack = " ".join([
            pid, p.get("title", ""), p.get("type", ""), p.get("path", ""),
            " ".join(p.get("tags", [])), " ".join(p.get("stack", [])),
        ]).lower()
        if needle in haystack:
            hits.append(p)
    if as_json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return 0 if hits else 3
    if not hits:
        print(f"(nothing matches {keyword!r})")
        return 3
    for p in hits:
        print(f"{p['id']}: {p.get('title', '')}")
        print(f"  path: {p.get('path')}")
        hint = "ws.py handoff " + p["id"]
        print(f"  next: {hint}")
    return 0


def cmd_show(root: Path, index: dict, target: str) -> int:
    entry = resolve(root, index, target)
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    pack = read_memory(root, entry)
    if pack.memory_path:
        head = pack.memory_path.read_text(encoding="utf-8").strip().splitlines()
        print("\n-- first lines of the handoff pack --")
        print("\n".join(head[:12]))
    return 0


# --------------------------------------------------------------------------- #
# Mutations
# --------------------------------------------------------------------------- #

def cmd_new(root: Path, index: dict, title: str, slug: str | None, ptype: str,
            status: str, tags: list[str], stack: list[str]) -> int:
    pid = slug or slugify(title)
    if not SLUG_RE.match(pid):
        fail(f"invalid slug {pid!r}: use lowercase letters, digits and dashes", 2)
    if pid in index["projects"]:
        fail(f"project {pid!r} already exists", 1)

    rel = f"{PROJECTS_DIR}/{pid}"
    proj_dir = root / rel
    proj_dir.mkdir(parents=True, exist_ok=False)
    memory = proj_dir / MEMORY_NAME
    memory.write_text(
        MEMORY_TEMPLATE.format(
            title=title, goal="(one paragraph: what problem this project solves)",
            status=status, today=today(),
        ),
        encoding="utf-8",
    )
    (proj_dir / "README.md").write_text(f"# {title}\n\n(what this is)\n", encoding="utf-8")

    index["projects"][pid] = {
        "id": pid,
        "title": title,
        "status": status,
        "type": ptype,
        "path": rel,
        "memory": f"{rel}/{MEMORY_NAME}",
        "tags": tags,
        "stack": stack,
        "created": today(),
        "updated": today(),
    }
    save_index(root, index)
    print(f"created {rel}/")
    print(f"registered {pid} in {INDEX_NAME}")
    print(f"next: fill in {rel}/{MEMORY_NAME}, then `ws.py handoff {pid}`")
    return 0


def cmd_init(dest: str, title: str, force: bool) -> int:
    root = Path(dest).expanduser().resolve()
    if (root / INDEX_NAME).exists() and not force:
        fail(f"{root} already looks like a workspace; use --force", 1)
    (root / "assets" / "tools").mkdir(parents=True, exist_ok=True)
    # 把自己复制过去：新工作区必须自带这个 CLI，否则第一条命令就跑不了
    me = Path(__file__).resolve()
    target = root / "assets" / "tools" / "ws.py"
    if me != target.resolve():
        target.write_text(me.read_text(encoding="utf-8"), encoding="utf-8")
        target.chmod(0o755)
    (root / PROJECTS_DIR).mkdir(exist_ok=True)
    (root / SKILLS_DIR).mkdir(exist_ok=True)

    index = {"schema_version": INDEX_VERSION, "updated_at": now_iso(), "projects": {}}
    (root / INDEX_NAME).write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    readme = root / "README.md"
    if not readme.exists() or force:
        readme.write_text(
            f"# {title}\n\n"
            "An agent workspace: one JSON index, handoff packs per project.\n\n"
            "```bash\n"
            "python3 assets/tools/ws.py new \"First project\" --type backend\n"
            "python3 assets/tools/ws.py handoff first-project\n"
            "```\n\n"
            "Read `AGENTS.md` for the rules agents should follow here.\n",
            encoding="utf-8",
        )
    agents = root / "AGENTS.md"
    if not agents.exists() or force:
        agents.write_text(
            "# AGENTS.md\n\n"
            "This workspace keeps its state in `_index.json` and one handoff pack\n"
            "per project. Before touching a project, run:\n\n"
            "```bash\n"
            "python3 assets/tools/ws.py handoff <project-id>\n"
            "```\n\n"
            "Then update `## State` and `## Next steps` before you finish.\n\n"
            "Never use `ls`/`find` to discover projects - ask the index.\n",
            encoding="utf-8",
        )
    print(f"initialised workspace at {root}")
    print("  _index.json, AGENTS.md, README.md, projects/, skills/, assets/tools/")
    return 0


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def cmd_check(root: Path, index: dict, fix: bool) -> int:
    problems: list[str] = []
    projects = index["projects"]

    for pid, entry in sorted(projects.items()):
        proj_dir = root / entry.get("path", f"{PROJECTS_DIR}/{pid}")
        if not proj_dir.is_dir():
            problems.append(f"{pid}: path missing on disk ({proj_dir.relative_to(root)})")
            continue
        pack = read_memory(root, entry)
        if pack.memory_path is None:
            problems.append(f"{pid}: handoff pack missing")
        elif pack.missing_sections:
            problems.append(f"{pid}: pack missing sections: " + ", ".join(pack.missing_sections))

    on_disk = {p.name for p in (root / PROJECTS_DIR).iterdir() if p.is_dir()} \
        if (root / PROJECTS_DIR).is_dir() else set()
    unregistered = sorted(on_disk - set(projects))

    if fix and unregistered:
        for pid in unregistered:
            index["projects"][pid] = {
                "id": pid, "title": pid, "status": "active", "type": "unclassified",
                "path": f"{PROJECTS_DIR}/{pid}",
                "memory": f"{PROJECTS_DIR}/{pid}/{MEMORY_NAME}",
                "tags": [], "stack": [], "created": today(), "updated": today(),
            }
            memory = root / PROJECTS_DIR / pid / MEMORY_NAME
            if not memory.exists():
                memory.write_text(
                    MEMORY_TEMPLATE.format(title=pid, goal="(fill me in)",
                                           status="active", today=today()),
                    encoding="utf-8")
        save_index(root, index)
        print(f"fixed: registered {len(unregistered)} project(s)")
        unregistered = []          # repaired, so it is no longer a problem

    for pid in unregistered:
        problems.append(f"{pid}: directory exists but is not registered")

    # 用 pack 里显式的 "last touched: YYYY-MM-DD" 比较，不看文件 mtime ——
    # git clone 之后所有文件的 mtime 都是检出时间，按 mtime 判断会永远误报。
    for pid, entry in sorted(projects.items()):
        pack = read_memory(root, entry)
        if pack.memory_path is None:
            continue
        touched = re.search(r"last touched:\s*(\d{4}-\d{2}-\d{2})",
                            pack.memory_path.read_text(encoding="utf-8"))
        if touched and touched.group(1) > (entry.get("updated") or ""):
            print(f"note: {pid}: pack says last touched {touched.group(1)},"
                  f" index says {entry.get('updated')} (bump the index entry)")

    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print("  - " + p)
        return 1
    print(f"ok: {len(projects)} project(s), index and disk agree")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        # `ws` when installed, `ws.py` when run from a checkout
        prog=Path(sys.argv[0]).name,
        description="One entry point for an agent workspace: index + handoff packs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Commands")[1] if "Commands" in (__doc__ or "") else None,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--root", help="workspace root (default: search upwards)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="create a workspace skeleton")
    p.add_argument("dest")
    p.add_argument("--title", default="agent workspace")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("new", help="create and register a project")
    p.add_argument("title")
    p.add_argument("--slug")
    p.add_argument("--type", default="unclassified")
    p.add_argument("--status", default="active", choices=["active", "paused", "archived"])
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--stack", action="append", default=[])

    p = sub.add_parser("list", help="list projects")
    p.add_argument("--status", choices=["active", "paused", "archived"])
    p.add_argument("--type")

    p = sub.add_parser("find", help="search projects")
    p.add_argument("keyword")

    p = sub.add_parser("show", help="index entry + pack head")
    p.add_argument("target")

    p = sub.add_parser("handoff", help="print the handoff pack")
    p.add_argument("target")

    p = sub.add_parser("check", help="validate index and packs")
    p.add_argument("--fix", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "init":
        return cmd_init(args.dest, args.title, args.force)

    root = find_root(override=args.root)
    index = load_index(root)

    if args.cmd == "new":
        return cmd_new(root, index, args.title, args.slug, args.type, args.status,
                       args.tag, args.stack)
    if args.cmd == "list":
        return cmd_list(root, index, args.status, args.type, args.json)
    if args.cmd == "find":
        return cmd_find(root, index, args.keyword, args.json)
    if args.cmd == "show":
        return cmd_show(root, index, args.target)
    if args.cmd == "handoff":
        return cmd_handoff(root, index, args.target, args.json)
    if args.cmd == "check":
        return cmd_check(root, index, args.fix)
    fail(f"unknown command {args.cmd}", 2)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
