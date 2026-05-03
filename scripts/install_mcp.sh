#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER="${REPO_ROOT}/quiet_clock/mcp_server.py"

if codex mcp list 2>/dev/null | awk '{print $1}' | grep -qx 'quiet_clock'; then
  codex mcp remove quiet_clock >/dev/null
fi
codex mcp add quiet_clock -- python3 "$SERVER"
codex mcp list | sed -n '1,120p'
