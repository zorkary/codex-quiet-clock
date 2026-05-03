from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quiet_clock.mcp_server import handle_request


def result_payload(response):
    return json.loads(response["result"]["content"][0]["text"])


class McpServerTests(unittest.TestCase):
    def test_initialize(self) -> None:
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "x"}})
        self.assertEqual(response["result"]["serverInfo"]["name"], "quiet_clock")
        self.assertEqual(response["result"]["protocolVersion"], "x")

    def test_tools_list_contains_required_tools_with_read_only_annotations(self) -> None:
        response = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = response["result"]["tools"]
        names = {tool["name"] for tool in tools}
        self.assertGreaterEqual(names, {"now", "thread_timeline", "elapsed_since", "find_message", "staleness_report"})
        for tool in tools:
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["destructiveHint"])

    def test_call_now(self) -> None:
        response = handle_request({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "now", "arguments": {}}})
        result = result_payload(response)
        self.assertTrue(result["ok"])
        self.assertIn("utc", result["time"])
        self.assertIn("local", result["time"])

    def test_timeline_requires_thread_or_explicit_latest(self) -> None:
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "", "CODEX_SESSION_ID": ""}):
            response = handle_request({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "thread_timeline", "arguments": {}}})
        result = result_payload(response)
        self.assertFalse(result["ok"])
        self.assertIn("allow_latest=true", result["error"])

    def test_timeline_suppresses_snippets_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout-test.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-05-03T01:00:00Z",
                        "type": "event_msg",
                        "payload": {"type": "user_message", "message": "secret-ish message"},
                    }
                )
                + "\n"
            )
            response = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {
                        "name": "thread_timeline",
                        "arguments": {"thread_id": str(path), "include_snippets": False},
                    },
                }
            )
        result = result_payload(response)
        self.assertTrue(result["ok"])
        self.assertNotIn("rollout_path", result["thread"])
        self.assertNotIn("snippet", result["items"][0])

    def test_unknown_tool_returns_error(self) -> None:
        response = handle_request({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope", "arguments": {}}})
        self.assertIn("error", response)


if __name__ == "__main__":
    unittest.main()
