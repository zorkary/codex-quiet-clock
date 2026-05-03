#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT=$(printf '{"hook_event_name":"UserPromptSubmit","session_id":"test-session","turn_id":"test-turn","cwd":"%s","prompt":"hello"}' "$REPO_ROOT" | python3 "$REPO_ROOT/quiet_clock/hook.py")
printf '%s\n' "$OUT"
printf '%s' "$OUT" | grep -q 'Quiet Clock is active'
printf '%s' "$OUT" | grep -q 'quiet_clock.thread_timeline'
