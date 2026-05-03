#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "privacy_scan: not in a git repo" >&2
  exit 1
fi

tracked_files="$(mktemp)"
trap 'rm -f "$tracked_files"' EXIT
git ls-files > "$tracked_files"

fail=0
report() {
  echo "privacy_scan: $*" >&2
  fail=1
}

while IFS= read -r path; do
  case "$path" in
    .git/*|*.pyc|*/__pycache__/*) report "tracked generated/private path: $path" ;;
    *.sqlite|*.sqlite-*|*.jsonl) report "tracked runtime data file: $path" ;;
    */.codex/*|.codex/*) report "tracked Codex runtime path: $path" ;;
  esac
  case "$(basename "$path")" in
    config.toml|state_*.sqlite|rollout-*.jsonl|*.pem|*.key|id_rsa|id_ed25519) report "tracked sensitive-looking file: $path" ;;
  esac
done < "$tracked_files"

scan_content() {
  local pattern="$1"
  local label="$2"
  local matches
  matches="$(git grep -n -I -E "$pattern" -- . 2>/dev/null || true)"
  if [[ -n "$matches" ]]; then
    report "$label"
    printf '%s\n' "$matches" >&2
  fi
}

scan_literal() {
  local literal="$1"
  local label="$2"
  local matches
  matches="$(git grep -n -I -F "$literal" -- . 2>/dev/null || true)"
  if [[ -n "$matches" ]]; then
    report "$label"
    printf '%s\n' "$matches" >&2
  fi
}

scan_content '/Users/[A-Za-z0-9._-]+' 'absolute macOS user path found'
scan_content 'gh[oprsu]_[A-Za-z0-9_]{20,}' 'GitHub token-like secret found'
scan_content 'sk-[A-Za-z0-9_-]{20,}' 'OpenAI-style token-like secret found'
scan_content 'AKIA[0-9A-Z]{16}' 'AWS access-key-like secret found'
scan_content 'BEGIN (OPENSSH|RSA|EC|DSA|PRIVATE) KEY' 'private key material found'
scan_content 'rollout-[0-9]{4}-[0-9]{2}-[0-9]{2}T' 'Codex transcript dump reference found'

if [[ -f .privacy-denylist.local ]]; then
  while IFS= read -r term; do
    [[ -z "$term" || "$term" == \#* ]] && continue
    scan_literal "$term" "local denylist term found"
  done < .privacy-denylist.local
fi

if [[ "$fail" -ne 0 ]]; then
  exit 1
fi

echo "privacy_scan: ok"
