#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
plugin_root="$repo_root/plugins/quiet-clock"

required=(
  "$plugin_root/.codex-plugin/plugin.json"
  "$plugin_root/.mcp.json"
  "$plugin_root/hooks/hooks.json"
  "$plugin_root/quiet_clock/__init__.py"
  "$plugin_root/quiet_clock/hook.py"
  "$plugin_root/quiet_clock/mcp_server.py"
  "$plugin_root/quiet_clock/time_context.py"
  "$plugin_root/quiet_clock/transcript.py"
)

for path in "${required[@]}"; do
  [[ -f "$path" ]] || { echo "check_plugin_package: missing $path" >&2; exit 1; }
done

python3 -m json.tool "$plugin_root/.codex-plugin/plugin.json" >/dev/null
python3 -m json.tool "$plugin_root/.mcp.json" >/dev/null
python3 -m json.tool "$plugin_root/hooks/hooks.json" >/dev/null

for file in __init__.py hook.py mcp_server.py time_context.py transcript.py; do
  diff -u "$repo_root/quiet_clock/$file" "$plugin_root/quiet_clock/$file" >/dev/null || {
    echo "check_plugin_package: plugin quiet_clock/$file is out of sync with root package" >&2
    exit 1
  }
done

printf '%s\n' '{"hook_event_name":"UserPromptSubmit","session_id":"plugin-check","turn_id":"turn-1"}' \
  | (cd "$plugin_root" && python3 quiet_clock/hook.py) \
  | python3 -m json.tool >/dev/null

echo "check_plugin_package: ok"
