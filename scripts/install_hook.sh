#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${CODEX_HOME:-$HOME/.codex}/config.toml"
HOOK_CMD="python3 ${REPO_ROOT}/quiet_clock/hook.py"
BEGIN="# BEGIN QUIET_CLOCK HOOK"
END="# END QUIET_CLOCK HOOK"
BLOCK=$(cat <<BLOCK_EOF
${BEGIN}
[[hooks.UserPromptSubmit]]
matcher = ""

[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "${HOOK_CMD}"
timeoutSec = 2
async = false
statusMessage = "Quiet Clock"
${END}
BLOCK_EOF
)

mkdir -p "$(dirname "$CONFIG")"
touch "$CONFIG"

echo "Quiet Clock will add this marked block to $CONFIG:" >&2
printf '%s\n' "$BLOCK" >&2

python3 - "$CONFIG" "$BEGIN" "$END" "$BLOCK" <<'PY'
from __future__ import annotations
import sys
from pathlib import Path

config = Path(sys.argv[1])
begin = sys.argv[2]
end = sys.argv[3]
block = sys.argv[4]
text = config.read_text() if config.exists() else ""
lines = text.splitlines()
out = []
skip = False
for line in lines:
    if line.strip() == begin:
        skip = True
        continue
    if skip and line.strip() == end:
        skip = False
        continue
    if not skip:
        out.append(line)
new_text = "\n".join(out).rstrip()
if new_text:
    new_text += "\n\n"
new_text += block.rstrip() + "\n"
config.write_text(new_text)
PY

echo "Installed Quiet Clock UserPromptSubmit hook."
