# Runtime Notes

Quiet Clock uses Codex hooks and MCP because those extension points exist today. It does not assume Codex lacks timestamps internally; local session logs can already contain timestamped events. The hook provides lightweight, predictable timing context at prompt submission time; the MCP provides deeper chronology lookup only when needed.

This split keeps the default context small while making exact timing available through an explicit read-only interface instead of ad hoc transcript spelunking.

A future Codex runtime could expose basic timing as hidden message metadata or a native transcript/timeline API directly:

- message creation time
- local timezone/date context
- turn index
- elapsed time since prior user turn
- compact compaction notes for long pauses and date boundaries

In that shape, a tool like Quiet Clock might shrink to a thin compatibility layer or disappear entirely. The common case would not require reconstructing timing from local transcript files.

Quiet Clock is a local implementation of that hook-plus-tool pattern, not a claim that runtime-level timing does not exist.
