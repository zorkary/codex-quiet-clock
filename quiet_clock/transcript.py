from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
STATE_DB = CODEX_HOME / "state_5.sqlite"
SESSIONS_ROOT = CODEX_HOME / "sessions"
DEFAULT_SNIPPET_CHARS = 240
MAX_SNIPPET_CHARS = 1000


@dataclass(frozen=True)
class ThreadRef:
    thread_id: str
    rollout_path: str
    cwd: str = ""
    title: str = ""
    updated_at_ms: int | None = None

    def as_dict(self, include_path: bool = False) -> dict[str, Any]:
        value: dict[str, Any] = {
            "thread_id": self.thread_id,
            "cwd": self.cwd,
            "title": self.title,
            "updated_at_ms": self.updated_at_ms,
        }
        if include_path:
            value["rollout_path"] = self.rollout_path
        return value


@dataclass(frozen=True)
class TimelineItem:
    id: str
    role: str
    timestamp: datetime
    text: str
    source: str
    turn_id: str | None = None
    item_type: str | None = None

    def as_dict(self, max_chars: int = DEFAULT_SNIPPET_CHARS, include_snippet: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "id": self.id,
            "role": self.role,
            "timestamp_utc": self.timestamp.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "turn_id": self.turn_id,
            "type": self.item_type,
            "source": self.source,
        }
        if include_snippet:
            value["snippet"] = compact_text(self.text, normalize_snippet_chars(max_chars))
        return value


def normalize_snippet_chars(value: Any, default: int = DEFAULT_SNIPPET_CHARS) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, min(parsed, MAX_SNIPPET_CHARS))


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def compact_text(text: str, max_chars: int = DEFAULT_SNIPPET_CHARS) -> str:
    if max_chars <= 0:
        return ""
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max(0, max_chars - 1)].rstrip() + "..."


def text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
        return "\n".join(parts)
    return ""


def iter_jsonl_records(path: str | os.PathLike[str], max_bytes: int | None = None) -> Iterable[tuple[int, dict[str, Any]]]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return
    start = 0
    if max_bytes is not None:
        size = p.stat().st_size
        start = max(0, size - max_bytes)
    with p.open("rb") as fh:
        if start:
            fh.seek(start)
            fh.readline()  # discard partial line
        for line_no, raw in enumerate(fh, start=1):
            if not raw.strip():
                continue
            try:
                yield line_no, json.loads(raw)
            except json.JSONDecodeError:
                continue


def timeline_item_from_record(line_no: int, record: dict[str, Any], include_tools: bool = False) -> TimelineItem | None:
    timestamp = parse_timestamp(record.get("timestamp"))
    rtype = record.get("type")
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}

    if rtype == "event_msg":
        ptype = payload.get("type")
        if ptype == "user_message":
            return TimelineItem(
                id=f"event:{line_no}",
                role="user",
                timestamp=timestamp,
                text=payload.get("message") or "",
                source="event_msg.user_message",
                item_type="message",
            )
        if ptype == "agent_message":
            return TimelineItem(
                id=f"event:{line_no}",
                role="assistant",
                timestamp=timestamp,
                text=payload.get("message") or "",
                source="event_msg.agent_message",
                item_type="message",
            )
        if ptype in {"task_started", "task_complete", "context_compacted", "thread_rolled_back"}:
            turn_id = payload.get("turn_id")
            return TimelineItem(
                id=f"event:{line_no}",
                role="system",
                timestamp=timestamp,
                text=ptype,
                source=f"event_msg.{ptype}",
                turn_id=turn_id,
                item_type=ptype,
            )

    if rtype == "turn_context":
        turn_id = payload.get("turn_id")
        return TimelineItem(
            id=f"turn:{turn_id or line_no}",
            role="system",
            timestamp=timestamp,
            text=f"turn_context cwd={payload.get('cwd', '')} model={payload.get('model', '')}",
            source="turn_context",
            turn_id=turn_id,
            item_type="turn_context",
        )

    if rtype == "response_item":
        ptype = payload.get("type")
        if ptype == "message":
            role = payload.get("role") or "unknown"
            if role == "developer":
                return None
            text = text_from_content(payload.get("content"))
            return TimelineItem(
                id=payload.get("id") or f"response:{line_no}",
                role=role,
                timestamp=timestamp,
                text=text,
                source="response_item.message",
                item_type="message",
            )
        if include_tools and ptype in {"function_call", "function_call_output", "custom_tool_call_output"}:
            name = payload.get("name") or payload.get("call_id") or ptype
            return TimelineItem(
                id=payload.get("id") or payload.get("call_id") or f"tool:{line_no}",
                role="tool",
                timestamp=timestamp,
                text=str(name),
                source=f"response_item.{ptype}",
                item_type=ptype,
            )

    return None


def load_timeline(path: str | os.PathLike[str], include_tools: bool = False, max_bytes: int | None = None) -> list[TimelineItem]:
    items: list[TimelineItem] = []
    seen_user_agent: set[tuple[str, str, str]] = set()
    for line_no, record in iter_jsonl_records(path, max_bytes=max_bytes):
        item = timeline_item_from_record(line_no, record, include_tools=include_tools)
        if not item:
            continue
        if item.role in {"user", "assistant"}:
            key = (item.role, item.timestamp.isoformat(), compact_text(item.text, 500))
            if key in seen_user_agent:
                continue
            seen_user_agent.add(key)
        items.append(item)
    items.sort(key=lambda item: item.timestamp)
    return items


def state_db_connection() -> sqlite3.Connection | None:
    if not STATE_DB.exists():
        return None
    try:
        return sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
    except sqlite3.Error:
        return None


def latest_rollout_file() -> str | None:
    if not SESSIONS_ROOT.exists():
        return None
    candidates = list(SESSIONS_ROOT.rglob("rollout-*.jsonl"))
    if not candidates:
        return None
    return str(max(candidates, key=lambda p: p.stat().st_mtime))


def resolve_thread(thread_id: str | None = None, allow_latest: bool = False) -> ThreadRef | None:
    env_thread = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    target = thread_id or env_thread or ""
    if target and Path(target).exists():
        return ThreadRef(thread_id=Path(target).stem, rollout_path=target)

    con = state_db_connection()
    if con:
        try:
            if target:
                row = con.execute(
                    "select id, rollout_path, cwd, coalesce(title, ''), updated_at_ms from threads where id = ? limit 1",
                    (target,),
                ).fetchone()
            elif allow_latest:
                row = con.execute(
                    "select id, rollout_path, cwd, coalesce(title, ''), updated_at_ms from threads where rollout_path is not null order by updated_at_ms desc limit 1"
                ).fetchone()
            else:
                row = None
            if row and row[1]:
                return ThreadRef(thread_id=row[0], rollout_path=row[1], cwd=row[2] or "", title=row[3] or "", updated_at_ms=row[4])
        except sqlite3.Error:
            pass
        finally:
            con.close()

    if allow_latest:
        fallback = latest_rollout_file()
        if fallback:
            return ThreadRef(thread_id=Path(fallback).stem, rollout_path=fallback)
    return None


def missing_thread_error() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "No Codex thread transcript found. Pass thread_id from Quiet Clock hook context, or set allow_latest=true for explicit latest-thread lookup.",
    }


def find_messages(
    query: str,
    role: str | None = None,
    limit: int = 10,
    thread_id: str | None = None,
    allow_latest: bool = False,
    include_snippets: bool = True,
    snippet_chars: int = DEFAULT_SNIPPET_CHARS,
    debug_paths: bool = False,
) -> dict[str, Any]:
    ref = resolve_thread(thread_id, allow_latest=allow_latest)
    if not ref:
        return {**missing_thread_error(), "matches": []}
    items = load_timeline(ref.rollout_path, include_tools=False, max_bytes=None)
    query_terms = [term.lower() for term in query.split() if term.strip()]
    matches = []
    for item in items:
        if role and item.role != role:
            continue
        haystack = item.text.lower()
        if not query_terms or all(term in haystack for term in query_terms):
            matches.append(item)
    matches = matches[-max(1, min(limit, 50)) :]
    return {
        "ok": True,
        "thread": ref.as_dict(include_path=debug_paths),
        "count": len(matches),
        "matches": [item.as_dict(snippet_chars, include_snippet=include_snippets) for item in matches],
    }
