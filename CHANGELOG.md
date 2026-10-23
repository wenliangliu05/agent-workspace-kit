# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- MCP wrapper so agents can call `handoff` as a tool instead of a shell command.
- `ws archive <id>` and `ws handoff --since <duration>`.

### Changed

- The README is now Chinese-first; the earlier English text is kept only in git
  history (it was never a second supported document).
- Dropped build artifacts that had been committed by accident (`*.egg-info/`,
  `build/`) and added them to `.gitignore`.

## [0.2.0] — 2026-10-23

### Added

- **Installable package.** `pipx install git+https://github.com/wenliangliu05/agent-workspace-kit`
  (or `pip install .`) exposes a `ws` console script; the module still lives at
  `assets/tools/ws.py` so a plain checkout keeps working without installing.
- `pyproject.toml` with project metadata and a repo-level lint policy (Python 3.10, 100 columns).
- `make lint` (ruff) and a lint step in CI, before the tests.
- `docs/demo.svg` — a terminal rendering of a real `handoff`, used in the README.
- `CHANGELOG.md`, `CONTRIBUTING.md`.

### Changed

- Slugs are Unicode-friendly: `ws new "发票导入器"` now works, not just ASCII titles.
- `check` compares the pack's explicit `last touched:` line instead of file mtimes
  (after a `git clone`, every mtime is the checkout time — the old check could never be right).
- `handoff` prints the project header with status and type on one line.

### Fixed

- `fail()` was annotated `-> "NoReturn"` without importing `NoReturn` (undefined name).
- `check --fix` still reported the directories it had just repaired, so it exited 1 after a successful repair.
- `init` created `assets/tools/` but did not copy the CLI into it, so the first command in a
  freshly initialised workspace failed.

## [0.1.0] — 2026-10-22

### Added

- First public cut: a JSON index (`_index.json`) plus one six-section handoff pack per project.
- CLI with `init`, `new`, `list`, `find`, `show`, `handoff`, `check`; `--root` discovery and
  `--json` output; exit codes `0/1/2/3` suitable for CI.
- Two demo projects (`demo-api`, `demo-cli`) and one example skill (`debugging`).
- 20 unit tests and a GitHub Actions matrix (3.10 / 3.11 / 3.13 and Windows).
- MIT license.

[Unreleased]: https://github.com/wenliangliu05/agent-workspace-kit/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/wenliangliu05/agent-workspace-kit/releases/tag/v0.2.0
[0.1.0]: https://github.com/wenliangliu05/agent-workspace-kit/commits/main
