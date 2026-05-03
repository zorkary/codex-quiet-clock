#!/usr/bin/env bash
set -euo pipefail

CONFIG="${CODEX_HOME:-$HOME/.codex}/config.toml"
BEGIN="# BEGIN QUIET_CLOCK HOOK"
END="# END QUIET_CLOCK HOOK"

if [ ! -f "$CONFIG" ]; then
  echo "No Codex config found at $CONFIG"
  exit 0
fi

python3 - "$CONFIG" "$BEGIN" "$END" <<'PY'
from __future__ import annotations
import sys
from pathlib import Path

config = Path(sys.argv[1])
begin = sys.argv[2]
end = sys.argv[3]
lines = config.read_text().splitlines()
out = []
skip = False
removed = False
for line in lines:
    if line.strip() == begin:
        skip = True
        removed = True
        continue
    if skip and line.strip() == end:
        skip = False
        continue
    if not skip:
        out.append(line)
config.write_text("\n".join(out).rstrip() + "\n")
print("Removed Quiet Clock hook." if removed else "Quiet Clock hook block was not present.")
PY
