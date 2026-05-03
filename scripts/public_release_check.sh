#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python3 -m unittest discover -s tests -v
bash scripts/smoke_hook.sh >/tmp/quiet-clock-smoke-hook.out
bash scripts/smoke_mcp.sh >/tmp/quiet-clock-smoke-mcp.out
git diff --check
bash scripts/privacy_scan.sh

if [[ -n "$(git status --short)" ]]; then
  echo "public_release_check: repo has uncommitted changes" >&2
  git status --short >&2
  exit 1
fi

tracked="$(git ls-files)"
if printf '%s\n' "$tracked" | grep -E '(^|/)(__pycache__|\.pytest_cache|\.venv|\.codex)(/|$)' >/dev/null; then
  echo "public_release_check: generated/private directory is tracked" >&2
  exit 1
fi

required=(README.md LICENSE PRIVACY.md SECURITY.md docs/runtime-notes.md .github/workflows/ci.yml)
for path in "${required[@]}"; do
  [[ -f "$path" ]] || { echo "public_release_check: missing $path" >&2; exit 1; }
done

echo "public_release_check: ok"
