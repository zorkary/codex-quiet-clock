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

## Plugin Packaging Status

Codex plugin docs describe bundled MCP servers and lifecycle hook config, but current local validation is mixed on Codex `0.128.0-alpha.1`:

- Direct hook install works.
- Direct MCP install works.
- Plugin-packaged MCP works when the plugin is present in the installed plugin cache.
- Plugin-packaged `UserPromptSubmit` hooks did not execute in `codex exec` during controlled marker-file tests.
- Local `codex plugin marketplace add` registers the marketplace, but does not appear to install or enable local plugin components by itself.

Until that runtime path is clearer, Quiet Clock treats plugin packaging as experimental and keeps direct hook/MCP installation as the supported path.
