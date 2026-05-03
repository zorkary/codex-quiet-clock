#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quiet_clock.time_context import build_hook_context, render_hook_context


def safe_output(text: str) -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": text,
        }
    }


def main() -> int:
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
        if not isinstance(hook_input, dict):
            hook_input = {}
        context = build_hook_context(hook_input)
        text = render_hook_context(context)
        print(json.dumps(safe_output(text), separators=(",", ":")))
        return 0
    except Exception as exc:  # pragma: no cover - hook must not break prompt submission
        fallback = (
            "Quiet Clock hook encountered a non-blocking error: "
            f"{type(exc).__name__}. Use quiet_clock.now or quiet_clock.staleness_report if available."
        )
        print(json.dumps(safe_output(fallback), separators=(",", ":")))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
