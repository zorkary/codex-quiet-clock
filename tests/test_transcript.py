from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quiet_clock.transcript import find_messages, load_timeline, resolve_thread


class TranscriptTests(unittest.TestCase):
    def test_load_timeline_from_event_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps({"timestamp": "2026-05-03T01:00:00Z", "type": "event_msg", "payload": {"type": "user_message", "message": "hello clock"}}),
                        json.dumps({"timestamp": "2026-05-03T01:00:02Z", "type": "event_msg", "payload": {"type": "agent_message", "message": "hello back"}}),
                        json.dumps({"timestamp": "2026-05-03T01:00:03Z", "type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-1"}}),
                    ]
                )
                + "\n"
            )
            items = load_timeline(path)
            self.assertEqual([item.role for item in items], ["user", "assistant", "system"])
            self.assertEqual(items[2].turn_id, "turn-1")

    def test_resolve_thread_accepts_existing_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout-test.jsonl"
            path.write_text("")
            ref = resolve_thread(str(path))
            self.assertIsNotNone(ref)
            self.assertEqual(ref.rollout_path, str(path))

    def test_resolve_thread_does_not_default_to_latest(self) -> None:
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "", "CODEX_SESSION_ID": ""}):
            self.assertIsNone(resolve_thread())

    def test_find_messages_can_suppress_snippets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout-test.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-05-03T01:00:00Z",
                        "type": "event_msg",
                        "payload": {"type": "user_message", "message": "private timing question"},
                    }
                )
                + "\n"
            )
            result = find_messages("timing", thread_id=str(path), include_snippets=False)
            self.assertTrue(result["ok"])
            self.assertNotIn("snippet", result["matches"][0])
            self.assertNotIn("rollout_path", result["thread"])


if __name__ == "__main__":
    unittest.main()
