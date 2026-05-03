# Runtime Notes

Quiet Clock uses Codex hooks and MCP because those extension points exist today. The hook provides lightweight timing context at prompt submission time; the MCP provides deeper chronology lookup only when needed.

This split keeps the default context small while still making exact timing available.

A future Codex runtime could expose basic timing as hidden message metadata directly:

- message creation time
- local timezone/date context
- turn index
- elapsed time since prior user turn
- compact compaction notes for long pauses and date boundaries

In that shape, a tool like Quiet Clock would still be useful for older timeline queries, but the common case would not require reconstructing timing from local transcript files.

Quiet Clock is a local implementation of that hook-plus-tool pattern, not a replacement for runtime-level metadata.
