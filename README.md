# Quiet Clock

A local hook + read-only MCP that makes Codex thread timing predictable and model-usable.

Quiet Clock does not claim Codex lacks timestamps. Codex may already record timing in local session logs or runtime state. Quiet Clock adds a predictable model-facing layer: a tiny hook for current timing context and a read-only lookup surface for exact chronology when needed. Without a layer like this, agents may infer timing from message order, current environment dates, or file/tool artifacts, but that is not the same as reliable per-message chat chronology. It is intentionally small: no daemon, no network service, no memory system, no background watcher.

## What It Adds

Quiet Clock has two pieces:

- A Codex `UserPromptSubmit` hook that injects compact current timing context on each user prompt.
- A local stdio MCP server named `quiet_clock` that reads local Codex session state for timeline/history tools when exact chronology matters.

The hook gives Codex a small model-visible note with current UTC/local time, timezone, local date, session/thread id, turn id, elapsed time since the previous user prompt, and stale/date-boundary hints. It is not a full transcript timeline.

The MCP provides read-only tools:

- `now` for current UTC/local time.
- `thread_timeline` for compact chronology.
- `elapsed_since` for elapsed time since a message, turn, or query match.
- `find_message` for prior message lookup.
- `staleness_report` for long pauses, day changes, stale-context risk, and exact-date hints.

## Demo

Hook context looks like this in model-visible context:

```text
Quiet Clock is active.
Now UTC: 2026-05-03T06:18:13Z.
Now local: 2026-05-02T23:18:13-07:00 (America/Los_Angeles); local date 2026-05-02.
Session/thread id: 019...
Current turn id: 019...
Elapsed since previous user prompt: 20m 45s.
Use the quiet_clock MCP instead of guessing for timing/history questions.
```

A tool result from `quiet_clock.now` looks like:

```json
{
  "ok": true,
  "time": {
    "utc": "2026-05-03T06:18:13Z",
    "local": "2026-05-02T23:18:13-07:00",
    "timezone": "America/Los_Angeles",
    "local_date": "2026-05-02"
  }
}
```

## Requirements

- macOS or another Unix-like environment.
- Python 3.11+.
- Codex CLI/app with hooks and MCP support.
- No Python package dependencies.

## Install From A Fresh Clone

This is the fully validated path. It installs both the hook and the MCP server directly into local Codex config.

```bash
git clone https://github.com/zorkary/codex-quiet-clock.git quiet-clock
cd quiet-clock
python3 -m unittest discover -s tests -v
scripts/install_hook.sh
scripts/install_mcp.sh
```

The hook installer writes a marked Quiet Clock block to `~/.codex/config.toml`. The MCP installer registers the server equivalent to:

```bash
codex mcp add quiet_clock -- python3 /path/to/quiet-clock/quiet_clock/mcp_server.py
```

If you move the checkout, rerun both installers.

## Experimental Plugin Marketplace Package

```bash
codex plugin marketplace add zorkary/codex-quiet-clock
```

This registers the Quiet Clock plugin marketplace with Codex. The plugin package is self-contained and includes bundled lifecycle config (`./hooks/hooks.json`) plus a bundled stdio MCP server config (`./.mcp.json`).

As of Codex `0.128.0-alpha.1`, live validation confirms the plugin-packaged MCP can load from an installed plugin cache, but plugin-packaged `UserPromptSubmit` hook activation is not yet proven in `codex exec`. This appears to match upstream issue [openai/codex#16430](https://github.com/openai/codex/issues/16430). Use the direct install path above for complete Quiet Clock behavior today.

Observed plugin-runtime caveats:

- `codex plugin marketplace add` for a local marketplace registers the marketplace in Codex config; it does not, by itself, activate Quiet Clock in `codex exec`.
- `codex plugin marketplace upgrade` currently rejects local marketplaces because it expects a Git marketplace.
- A minimal hook-only plugin with `hooks/hooks.json` did not execute its `UserPromptSubmit` hook in `codex exec`, even with the plugin enabled and installed into the expected cache path.
- The same hook logic works through direct Codex hook configuration.

For now, treat plugin packaging as a compatibility experiment and use the direct installer scripts for the working product.

## Verify Installation

```bash
python3 -m unittest discover -s tests -v
scripts/smoke_hook.sh
scripts/smoke_mcp.sh
codex mcp list
```

Expected MCP list entry:

```text
quiet_clock   python3   /path/to/quiet-clock/quiet_clock/mcp_server.py   enabled
```

Live hook probe:

```bash
codex exec --ephemeral --sandbox read-only "If Quiet Clock hook context is visible, answer exactly QUIET_CLOCK_VISIBLE. Otherwise answer NO."
```

Live MCP probe:

```bash
codex exec --ephemeral --sandbox read-only "Use the quiet_clock.now tool once. Then answer TOOL_USED if it succeeded, otherwise TOOL_FAILED."
```

If `quiet_clock` does not appear in an already-open Codex chat, restart Codex or start a fresh chat.

## How To Use It

Usually you do not ask for Quiet Clock directly. The hook gives Codex minimal current timing context automatically.

Ask explicit timing questions when needed:

```text
how long ago did I say that?
```

```text
find when I first mentioned the MCP cancellation issue
```

```text
did this thread go stale overnight?
```

Codex should use the MCP tools instead of guessing or spelunking through local files when exact timing or chronology matters.

## Privacy Defaults

Timeline tools should receive the session/thread id from the hook context. They do not silently fall back to the latest local thread unless `allow_latest=true` is passed explicitly. They also refuse arbitrary transcript paths; transcript reads are limited to Codex rollout JSONL files under the configured Codex sessions root.

Timeline outputs support:

- `include_snippets=false` to suppress message snippets.
- `snippet_chars` to cap snippet length.
- `debug_paths=true` to include raw transcript paths only when debugging.

See `PRIVACY.md` for the full privacy model.

## Uninstall

Remove the hook block:

```bash
scripts/uninstall_hook.sh
```

Remove the MCP registration:

```bash
codex mcp remove quiet_clock
```

## Development

```bash
python3 -m unittest discover -s tests -v
scripts/smoke_hook.sh
scripts/smoke_mcp.sh
scripts/public_release_check.sh
```

Main files:

- `quiet_clock/hook.py`: Codex hook entrypoint.
- `quiet_clock/mcp_server.py`: stdio MCP server.
- `plugins/quiet-clock/`: self-contained Codex plugin package.
- `quiet_clock/transcript.py`: local Codex transcript/session readers.
- `quiet_clock/time_context.py`: timing context and stale/date-boundary logic.

## Safety Model

Normal Quiet Clock operation is read-only.

It may read Codex hook input, local Codex transcript/session files, and the local Codex session index in read-only SQLite mode.

It does not call the network, run a daemon, create cron jobs, create launch agents, run watchers, write memory, mutate repo files during normal use, push to GitHub, or contact third parties.

The only intentional writes are install/uninstall/configuration operations.

## Runtime Notes

Quiet Clock uses hooks and MCP because those extension points are available today. In a future runtime, basic message timing may be exposed directly as hidden metadata or a native transcript API; Quiet Clock is a local approximation of that interface. See `docs/runtime-notes.md`.

## Troubleshooting

### MCP tool calls are cancelled

Make sure tools include read-only MCP annotations:

```json
{
  "readOnlyHint": true,
  "destructiveHint": false,
  "idempotentHint": true,
  "openWorldHint": false
}
```

Without those annotations, Codex may list tools but cancel calls before sending `tools/call` to the server.

### Hook is not visible

Run `scripts/smoke_hook.sh`, then confirm the marked hook block exists in `~/.codex/config.toml`.

### MCP is registered but unavailable in a chat

Run `codex mcp list`. If `quiet_clock` appears there, restart Codex or start a fresh chat. Existing sessions may not pick up newly registered MCP namespaces immediately.

## Limits

Quiet Clock does not add hidden per-message envelope metadata to Codex internals, and it does not depend on proving what timing metadata Codex may already have internally. It uses Codex hook `additionalContext`, which is model-visible context but not normal chat text.

The MCP reconstructs timeline information from local Codex session state and JSONL transcript files. If those files are unavailable or the runtime layout changes, Quiet Clock returns the best available timing context rather than blocking the turn.
