"""Tests for the workspace CLI.

Run with:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "assets" / "tools" / "ws.py"


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Invoke the CLI the way an agent would: a real subprocess in a directory."""
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False, cwd=str(cwd or REPO), capture_output=True, text=True,
    )


class RepoIsAWorkspace(unittest.TestCase):
    """The repository itself must stay a valid, checkable workspace."""

    def test_handoff_prints_three_blocks(self):
        result = run("handoff", "demo-api")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("== 1. project memory ==", result.stdout)
        self.assertIn("== 2. file map", result.stdout)
        self.assertIn("== 3. skills", result.stdout)

    def test_handoff_carries_the_gotchas(self):
        # The whole point: traps survive, not just filenames.
        out = run("handoff", "demo-api").stdout
        self.assertIn("synchronous on purpose", out)

    def test_check_passes_on_the_shipped_workspace(self):
        result = run("check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_list_shows_both_demos(self):
        out = run("list").stdout
        self.assertIn("demo-api", out)
        self.assertIn("demo-cli", out)

    def test_list_filters_by_status(self):
        out = run("list", "--status", "paused").stdout
        self.assertIn("demo-cli", out)
        self.assertNotIn("demo-api", out)

    def test_find_matches_tags_and_stack(self):
        self.assertIn("demo-cli", run("find", "logs").stdout)
        self.assertIn("demo-api", run("find", "sqlite").stdout)

    def test_find_without_hits_exits_3(self):
        self.assertEqual(run("find", "no-such-thing").returncode, 3)

    def test_unknown_project_exits_3(self):
        self.assertEqual(run("handoff", "nope").returncode, 3)

    def test_handoff_json_is_machine_readable(self):
        result = run("--json", "handoff", "demo-api")
        data = json.loads(result.stdout)
        self.assertEqual(data["project"]["id"], "demo-api")
        self.assertEqual(data["missing_sections"], [])
        self.assertTrue(data["file_map"])

    def test_show_prints_the_index_entry(self):
        data = json.loads(run("show", "demo-api").stdout.split("\n--")[0])
        self.assertEqual(data["status"], "active")


class FreshWorkspace(unittest.TestCase):
    """A workspace created from scratch must work with zero extra setup."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ws-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def init(self, name: str = "ws") -> Path:
        root = self.tmp / name
        result = run("init", str(root), "--title", "Test workspace")
        self.assertEqual(result.returncode, 0, result.stderr)
        return root

    def test_init_is_self_contained(self):
        root = self.init()
        self.assertTrue((root / "_index.json").is_file())
        self.assertTrue((root / "AGENTS.md").is_file())
        # The CLI must be copied in, or the first command in the new workspace fails.
        self.assertTrue((root / "assets" / "tools" / "ws.py").is_file())

    def test_new_registers_the_project_and_writes_a_pack(self):
        root = self.init()
        result = run("new", "Invoice importer", "--type", "backend",
                     "--stack", "python", "--tag", "etl", cwd=root)
        self.assertEqual(result.returncode, 0, result.stderr)
        index = json.loads((root / "_index.json").read_text(encoding="utf-8"))
        self.assertIn("invoice-importer", index["projects"])
        pack = root / "projects" / "invoice-importer" / "project_memory.md"
        self.assertTrue(pack.is_file())
        for section in ("Goal", "State", "Key files", "Gotchas", "Skills", "Next steps"):
            self.assertIn(f"## {section}", pack.read_text(encoding="utf-8"))

    def test_new_rejects_duplicates(self):
        root = self.init()
        run("new", "Thing", "--slug", "thing", cwd=root)
        self.assertEqual(run("new", "Thing again", "--slug", "thing", cwd=root).returncode, 1)

    def test_new_accepts_a_non_ascii_title(self):
        root = self.init()
        result = run("new", "发票导入器", "--type", "backend", cwd=root)
        self.assertEqual(result.returncode, 0, result.stderr)
        index = json.loads((root / "_index.json").read_text(encoding="utf-8"))
        self.assertEqual(list(index["projects"]), ["发票导入器"])

    def test_new_rejects_bad_slug(self):
        root = self.init()
        self.assertEqual(run("new", "X", "--slug", "Bad_Slug!", cwd=root).returncode, 2)

    def test_check_reports_a_pack_missing_a_section(self):
        root = self.init()
        run("new", "Thing", "--slug", "thing", cwd=root)
        pack = root / "projects" / "thing" / "project_memory.md"
        pack.write_text(
            pack.read_text(encoding="utf-8").replace("## Gotchas", "## Notes"),
            encoding="utf-8")
        result = run("check", cwd=root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Gotchas", result.stdout)

    def test_check_detects_an_unregistered_directory(self):
        root = self.init()
        (root / "projects" / "stray").mkdir()
        self.assertIn("not registered", run("check", cwd=root).stdout)

    def test_check_fix_registers_the_stray_directory(self):
        root = self.init()
        (root / "projects" / "stray").mkdir()
        self.assertEqual(run("check", "--fix", cwd=root).returncode, 0)
        index = json.loads((root / "_index.json").read_text(encoding="utf-8"))
        self.assertIn("stray", index["projects"])

    def test_handoff_works_from_a_subdirectory(self):
        root = self.init()
        run("new", "Thing", "--slug", "thing", cwd=root)
        # Agents call the tool from wherever they are; root discovery walks up.
        result = run("handoff", "thing", cwd=root / "projects" / "thing")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_root_flag_overrides_discovery(self):
        root = self.init()
        run("new", "Thing", "--slug", "thing", cwd=root)
        result = run("--root", str(root), "list", cwd=self.tmp)
        self.assertIn("thing", result.stdout)


if __name__ == "__main__":
    unittest.main()
