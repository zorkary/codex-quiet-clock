from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path

from quiet_clock.hook import main as hook_main
from quiet_clock.time_context import build_hook_context, human_duration, render_hook_context


class TimeContextTests(unittest.TestCase):
    def test_human_duration(self) -> None:
        self.assertEqual(human_duration(59), "59s")
        self.assertEqual(human_duration(60), "1m")
        self.assertEqual(human_duration(3661), "1h 1m")
        self.assertEqual(human_duration(172800), "2d")

    def test_missing_transcript_still_includes_mcp_affordance(self) -> None:
        now = datetime(2026, 5, 3, 5, 0, 0, tzinfo=timezone.utc)
        context = build_hook_context({"session_id": "s", "turn_id": "t"}, now=now)
        text = render_hook_context(context)
        self.assertIn("Quiet Clock is active", text)
        self.assertIn("quiet_clock.thread_timeline", text)
        self.assertIn("Transcript timing detail: not provided", text)

    def test_long_pause_and_date_boundary_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            transcript_root = Path(tmp) / "sessions"
            transcript_root.mkdir()
            transcript = transcript_root / "rollout-test.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-05-02T04:00:00.000Z",
                        "type": "event_msg",
                        "payload": {"type": "user_message", "message": "yesterday task"},
                    }
                )
                + "\n"
            )
            now = datetime(2026, 5, 3, 18, 0, 0, tzinfo=timezone.utc)
            with patch("quiet_clock.transcript.SESSIONS_ROOT", transcript_root):
                context = build_hook_context({"transcript_path": str(transcript)}, now=now)
            text = render_hook_context(context)
            self.assertIn("Elapsed since previous user prompt", text)
            self.assertTrue(any("Long pause" in note for note in context["notes"]))

    def test_hook_refuses_outside_transcript_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "rollout-test.jsonl"
            transcript.write_text("")
            context = build_hook_context({"transcript_path": str(transcript)})
            self.assertEqual(context["transcript_status"], "refused: outside Codex sessions root or not a rollout JSONL file")


if __name__ == "__main__":
    unittest.main()
