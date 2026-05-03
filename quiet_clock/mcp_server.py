#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quiet_clock.time_context import current_time_info, human_duration
from quiet_clock.transcript import (
    DEFAULT_SNIPPET_CHARS,
    find_messages,
    load_timeline,
    missing_thread_error,
    normalize_snippet_chars,
    resolve_thread,
)

SERVER_NAME = "quiet_clock"
SERVER_VERSION = "0.1.0"


def bool_arg(arguments: dict[str, Any], name: str, default: bool = False) -> bool:
    value = arguments.get(name, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def privacy_args(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "include_snippets": bool_arg(arguments, "include_snippets", True),
        "snippet_chars": normalize_snippet_chars(arguments.get("snippet_chars", DEFAULT_SNIPPET_CHARS)),
        "debug_paths": bool_arg(arguments, "debug_paths", False),
    }


def tool_now(arguments: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "time": current_time_info()}


def tool_thread_timeline(arguments: dict[str, Any]) -> dict[str, Any]:
    thread_id = arguments.get("thread_id") or None
    allow_latest = bool_arg(arguments, "allow_latest", False)
    last_n = int(arguments.get("last_n") or 25)
    include_tools = bool_arg(arguments, "include_tools", False)
    privacy = privacy_args(arguments)
    ref = resolve_thread(thread_id, allow_latest=allow_latest)
    if not ref:
        return {**missing_thread_error(), "items": []}
    items = load_timeline(ref.rollout_path, include_tools=include_tools, max_bytes=None)
    selected = items[-max(1, min(last_n, 200)) :]
    return {
        "ok": True,
        "thread": ref.as_dict(include_path=privacy["debug_paths"]),
        "count": len(selected),
        "items": [
            item.as_dict(privacy["snippet_chars"], include_snippet=privacy["include_snippets"])
            for item in selected
        ],
    }


def _find_item(arguments: dict[str, Any]):
    thread_id = arguments.get("thread_id") or None
    allow_latest = bool_arg(arguments, "allow_latest", False)
    ref = resolve_thread(thread_id, allow_latest=allow_latest)
    if not ref:
        return None, None, missing_thread_error()["error"]
    items = load_timeline(ref.rollout_path, include_tools=True, max_bytes=None)
    message_id = arguments.get("message_id") or ""
    turn_id = arguments.get("turn_id") or ""
    query = arguments.get("query") or ""
    if message_id:
        for item in items:
            if item.id == message_id:
                return ref, item, ""
    if turn_id:
        for item in reversed(items):
            if item.turn_id == turn_id or item.id == f"turn:{turn_id}":
                return ref, item, ""
    if query:
        terms = [term.lower() for term in query.split() if term.strip()]
        for item in reversed(items):
            haystack = item.text.lower()
            if terms and all(term in haystack for term in terms):
                return ref, item, ""
    return ref, None, "No matching message or turn found"


def tool_elapsed_since(arguments: dict[str, Any]) -> dict[str, Any]:
    privacy = privacy_args(arguments)
    ref, item, error = _find_item(arguments)
    if not item:
        return {"ok": False, "error": error}
    now = datetime.now(timezone.utc)
    elapsed_seconds = max(0, (now - item.timestamp).total_seconds())
    return {
        "ok": True,
        "thread": ref.as_dict(include_path=privacy["debug_paths"]) if ref else None,
        "target": item.as_dict(privacy["snippet_chars"], include_snippet=privacy["include_snippets"]),
        "elapsed_ms": int(elapsed_seconds * 1000),
        "elapsed_human": human_duration(elapsed_seconds),
        "now": current_time_info(now),
    }


def tool_find_message(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query") or "")
    role = arguments.get("role") or None
    limit = int(arguments.get("limit") or 10)
    thread_id = arguments.get("thread_id") or None
    allow_latest = bool_arg(arguments, "allow_latest", False)
    privacy = privacy_args(arguments)
    return find_messages(
        query=query,
        role=role,
        limit=max(1, min(limit, 50)),
        thread_id=thread_id,
        allow_latest=allow_latest,
        include_snippets=privacy["include_snippets"],
        snippet_chars=privacy["snippet_chars"],
        debug_paths=privacy["debug_paths"],
    )


def tool_staleness_report(arguments: dict[str, Any]) -> dict[str, Any]:
    thread_id = arguments.get("thread_id") or None
    allow_latest = bool_arg(arguments, "allow_latest", False)
    current_prompt = str(arguments.get("current_prompt") or "")
    privacy = privacy_args(arguments)
    ref = resolve_thread(thread_id, allow_latest=allow_latest)
    if not ref:
        return missing_thread_error()
    items = load_timeline(ref.rollout_path, include_tools=False, max_bytes=None)
    users = [item for item in items if item.role == "user"]
    now = datetime.now(timezone.utc)
    notes: list[str] = []
    long_gaps: list[dict[str, Any]] = []
    previous = None
    for item in users:
        if previous:
            delta = (item.timestamp - previous.timestamp).total_seconds()
            if delta >= 60 * 60:
                long_gaps.append(
                    {
                        "from": previous.as_dict(privacy["snippet_chars"], include_snippet=privacy["include_snippets"]),
                        "to": item.as_dict(privacy["snippet_chars"], include_snippet=privacy["include_snippets"]),
                        "elapsed_human": human_duration(delta),
                    }
                )
        previous = item
    if users:
        since_last = (now - users[-1].timestamp).total_seconds()
        if since_last >= 6 * 60 * 60:
            notes.append("Long pause since latest user message; live state may be stale.")
        if users[-1].timestamp.astimezone().date() != now.astimezone().date():
            notes.append("Local date changed since latest user message; clarify relative dates.")
    lowered = current_prompt.lower()
    if any(word in lowered for word in ["today", "yesterday", "tomorrow", "latest", "recent", "now"]):
        notes.append("Prompt contains relative timing language; use exact dates/times when answering.")
    return {
        "ok": True,
        "thread": ref.as_dict(include_path=privacy["debug_paths"]),
        "now": current_time_info(now),
        "latest_user": users[-1].as_dict(privacy["snippet_chars"], include_snippet=privacy["include_snippets"]) if users else None,
        "long_gaps": long_gaps[-10:],
        "notes": notes,
    }


THREAD_TOOL_OPTIONS: dict[str, Any] = {
    "thread_id": {"type": "string", "description": "Preferred. Pass the session/thread id from Quiet Clock hook context."},
    "allow_latest": {"type": "boolean", "description": "Explicitly allow fallback to the most recently updated local Codex thread."},
    "include_snippets": {"type": "boolean", "description": "Include compact message snippets. Defaults true."},
    "snippet_chars": {"type": "integer", "minimum": 0, "maximum": 1000, "description": "Maximum characters per snippet."},
    "debug_paths": {"type": "boolean", "description": "Include raw local transcript path for debugging. Defaults false."},
}


TOOLS: dict[str, tuple[str, dict[str, Any], Callable[[dict[str, Any]], dict[str, Any]]]] = {
    "now": (
        "Return current UTC/local time, timezone, local date, and process monotonic timestamp.",
        {"type": "object", "properties": {}, "additionalProperties": False},
        tool_now,
    ),
    "thread_timeline": (
        "Return compact chronology for a Codex thread.",
        {
            "type": "object",
            "properties": {
                **THREAD_TOOL_OPTIONS,
                "last_n": {"type": "integer", "minimum": 1, "maximum": 200},
                "include_tools": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        tool_thread_timeline,
    ),
    "elapsed_since": (
        "Return elapsed time since a message id, turn id, or query match.",
        {
            "type": "object",
            "properties": {
                **THREAD_TOOL_OPTIONS,
                "message_id": {"type": "string"},
                "turn_id": {"type": "string"},
                "query": {"type": "string"},
            },
            "additionalProperties": False,
        },
        tool_elapsed_since,
    ),
    "find_message": (
        "Find prior user or assistant messages by text.",
        {
            "type": "object",
            "properties": {
                **THREAD_TOOL_OPTIONS,
                "query": {"type": "string"},
                "role": {"type": "string", "enum": ["user", "assistant", "system", "tool"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        tool_find_message,
    ),
    "staleness_report": (
        "Report long pauses, day changes, stale context risk, and exact-date hints.",
        {
            "type": "object",
            "properties": {
                **THREAD_TOOL_OPTIONS,
                "current_prompt": {"type": "string"},
            },
            "additionalProperties": False,
        },
        tool_staleness_report,
    ),
}


def tool_list() -> list[dict[str, Any]]:
    annotations = {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
    return [
        {"name": name, "description": desc, "inputSchema": schema, "annotations": annotations}
        for name, (desc, schema, _func) in TOOLS.items()
    ]


def result_content(result: dict[str, Any]) -> dict[str, Any]:
    # Keep the response shape conservative for broad Codex MCP compatibility.
    # The JSON payload remains available in text content for callers to parse.
    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2, sort_keys=True)}],
        "isError": not bool(result.get("ok", True)),
    }


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        protocol = params.get("protocolVersion") or "2024-11-05"
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": protocol,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tool_list()}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        if name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {name}"},
            }
        try:
            result = TOOLS[name][2](arguments)
        except Exception as exc:  # pragma: no cover - MCP safety boundary
            result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        return {"jsonrpc": "2.0", "id": request_id, "result": result_content(result)}

    if request_id is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = handle_request(message)
        except Exception as exc:  # pragma: no cover - protocol fallback
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse/server error: {type(exc).__name__}: {exc}"},
            }
        if response is not None:
            print(json.dumps(response, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
