from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .transcript import TimelineItem, load_timeline

STALE_AFTER_SECONDS = 6 * 60 * 60
LONG_PAUSE_SECONDS = 60 * 60

MCP_AFFORDANCES = [
    "quiet_clock.now: current UTC/local time",
    "quiet_clock.thread_timeline: compact thread chronology; pass this session/thread id when available",
    "quiet_clock.elapsed_since: elapsed time since a message or turn; pass this session/thread id when available",
    "quiet_clock.find_message: locate prior messages by text; pass this session/thread id when available",
    "quiet_clock.staleness_report: stale context, long pauses, and date-boundary hints; pass this session/thread id when available",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def detect_local_timezone() -> str:
    tz_env = os.environ.get("TZ")
    if tz_env:
        return tz_env
    localtime = Path("/etc/localtime")
    try:
        target = os.path.realpath(localtime)
        marker = "/zoneinfo/"
        if marker in target:
            return target.split(marker, 1)[1]
    except OSError:
        pass
    local = datetime.now().astimezone()
    return local.tzname() or str(local.tzinfo) or "local"


def format_dt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def format_dt_local(value: datetime) -> str:
    return value.astimezone().isoformat(timespec="seconds")


def human_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s" if sec else f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 48:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h" if hours else f"{days}d"


def current_time_info(now: datetime | None = None) -> dict[str, Any]:
    now = now or utc_now()
    local = now.astimezone()
    return {
        "utc": format_dt_utc(now),
        "local": format_dt_local(now),
        "timezone": detect_local_timezone(),
        "local_date": local.date().isoformat(),
        "monotonic_seconds": time.monotonic(),
    }


def latest_user_before(items: list[TimelineItem], now: datetime) -> TimelineItem | None:
    users = [item for item in items if item.role == "user" and item.timestamp <= now]
    return users[-1] if users else None


def build_hook_context(hook_input: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or utc_now()
    transcript_path = hook_input.get("transcript_path") or ""
    timeline: list[TimelineItem] = []
    transcript_status = "not provided"
    if transcript_path:
        try:
            timeline = load_timeline(transcript_path, include_tools=False, max_bytes=5_000_000)
            transcript_status = "ok"
        except Exception as exc:  # pragma: no cover - defensive hook path
            transcript_status = f"unavailable: {type(exc).__name__}: {exc}"

    previous_user = latest_user_before(timeline, now)
    notes: list[str] = []
    elapsed: dict[str, Any] | None = None

    if previous_user:
        elapsed_seconds = (now - previous_user.timestamp).total_seconds()
        elapsed = {
            "seconds": int(max(0, elapsed_seconds)),
            "human": human_duration(elapsed_seconds),
            "previous_user_timestamp_utc": format_dt_utc(previous_user.timestamp),
            "previous_user_id": previous_user.id,
        }
        if elapsed_seconds >= STALE_AFTER_SECONDS:
            notes.append(
                "Long pause since prior user prompt; treat urgency and local state as potentially stale."
            )
        elif elapsed_seconds >= LONG_PAUSE_SECONDS:
            notes.append("Noticeable pause since prior user prompt; verify live state if it matters.")

        prev_local_date = previous_user.timestamp.astimezone().date()
        now_local_date = now.astimezone().date()
        if prev_local_date != now_local_date:
            notes.append(
                f"Local date changed since prior user prompt ({prev_local_date.isoformat()} -> {now_local_date.isoformat()}); resolve today/yesterday/tomorrow explicitly."
            )

    return {
        "time": current_time_info(now),
        "session_id": hook_input.get("session_id") or "",
        "turn_id": hook_input.get("turn_id") or "",
        "cwd": hook_input.get("cwd") or "",
        "transcript_path": transcript_path,
        "transcript_status": transcript_status,
        "elapsed_since_previous_user": elapsed,
        "notes": notes,
        "mcp_server": "quiet_clock",
        "mcp_affordances": MCP_AFFORDANCES,
    }


def render_hook_context(context: dict[str, Any]) -> str:
    time_info = context["time"]
    lines = [
        "Quiet Clock is active.",
        f"Now UTC: {time_info['utc']}.",
        f"Now local: {time_info['local']} ({time_info['timezone']}); local date {time_info['local_date']}.",
    ]
    if context.get("session_id"):
        lines.append(f"Session/thread id: {context['session_id']}.")
    if context.get("turn_id"):
        lines.append(f"Current turn id: {context['turn_id']}.")
    elapsed = context.get("elapsed_since_previous_user")
    if elapsed:
        lines.append(
            "Elapsed since previous user prompt: "
            f"{elapsed['human']} (previous user at {elapsed['previous_user_timestamp_utc']})."
        )
    if context.get("notes"):
        lines.append("Timing notes: " + " ".join(context["notes"]))
    if context.get("transcript_status") and context["transcript_status"] != "ok":
        lines.append(f"Transcript timing detail: {context['transcript_status']}.")
    lines.append(
        "Use the quiet_clock MCP instead of guessing for timing/history questions. "
        "For timeline/history tools, pass the session/thread id above when available; only use allow_latest=true when explicitly asking for latest-thread lookup. Tools: "
        + "; ".join(context["mcp_affordances"])
        + "."
    )
    return "\n".join(lines)
