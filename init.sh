#!/usr/bin/env bash
# Create a new workspace. Thin wrapper around `ws.py init`.
#
#   ./init.sh ~/my-workspace --title "My workspace"
#
# Windows: call `python3 assets/tools/ws.py init <dir>` directly.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 not found on PATH" >&2
  exit 2
fi

exec python3 "$here/assets/tools/ws.py" init "$@"
