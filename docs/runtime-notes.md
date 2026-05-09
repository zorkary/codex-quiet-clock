# Runtime Notes

Quiet Clock uses Codex hooks and MCP because those extension points exist today. It does not assume Codex lacks timestamps internally; local session logs can already contain timestamped events. The hook provides lightweight, predictable timing context at prompt submission time; the MCP provides deeper chronology lookup only when needed.

This split keeps the default context small while making exact timing available through an explicit read-only interface instead of ad hoc transcript spelunking. In baseline Codex sessions without Quiet Clock, the model may know message order and current environment dates, or infer timing from file/tool artifacts, but it should not be assumed to have reliable per-message chat timestamps in active context.

A future Codex runtime could expose basic timing as hidden message metadata or a native transcript/timeline API directly:

- message creation time
- local timezone/date context
- turn index
- elapsed time since prior user turn
- compact compaction notes for long pauses and date boundaries

In that shape, a tool like Quiet Clock might shrink to a thin compatibility layer or disappear entirely. The common case would not require reconstructing timing from local transcript files.

Quiet Clock is a local implementation of that hook-plus-tool pattern, not a claim that runtime-level timing does not exist.

## Plugin Packaging Status

Codex `0.130.0-alpha.5` moves plugin packaging closer to the shape Quiet Clock wants, but not far enough that plugin install should replace the direct install path yet.

- `codex features list` reports `hooks` and `plugins` as stable.
- `codex features list` reports `plugin_hooks` as under development.
- Upstream [openai/codex#19705](https://github.com/openai/codex/pull/19705) adds discovery/runtime plumbing for plugin-bundled hooks behind the `plugin_hooks` feature flag.
- Upstream [openai/codex#21447](https://github.com/openai/codex/pull/21447) makes bundled hooks visible in plugin detail views.
- Direct hook install works without feature flags.
- Direct MCP install works without feature flags.

That means Quiet Clock can keep the plugin bundle as a forward-compatible experiment, but should not make it the primary install flow until plugin hooks are stable by default. The direct hook + MCP scripts remain the supported path.

## Codex App-Server Notes

Codex `0.130` also exposes more app-server timing and thread-history shape:

- `codex app-server --listen ws://127.0.0.1:0` starts a local websocket server bound to loopback.
- `thread` objects include `createdAt` and `updatedAt`.
- `turn` objects include `startedAt`, `completedAt`, and `durationMs`.
- turn item loading supports `notLoaded`, `summary`, and `full` views.

Those APIs point toward a cleaner future implementation where Quiet Clock could query a supported app-server timeline instead of reconstructing timing from local session files. The current implementation stays conservative: read local Codex state, avoid daemons, avoid network services, and do not mutate transcripts.

`codex remote-control` is a separate experimental entrypoint that starts a headless, remotely controllable app-server and connects to ChatGPT remote control infrastructure. It may become important for mobile or hosted control-plane workflows, but Quiet Clock does not require it.
