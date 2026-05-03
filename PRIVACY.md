# Privacy

Quiet Clock is a local-only timing helper for Codex. It has no network client and no background service.

## What Quiet Clock Reads

During normal use, Quiet Clock may read:

- Codex hook input passed on stdin.
- Local Codex transcript/session files when a timeline tool needs chronology.
- The local Codex session index in read-only SQLite mode.

The `now` tool reads no transcript data.

## What Quiet Clock Writes

During normal hook and MCP operation, Quiet Clock writes nothing.

The install scripts intentionally update local Codex configuration:

- `scripts/install_hook.sh` adds a marked hook block to `~/.codex/config.toml`.
- `scripts/uninstall_hook.sh` removes only that marked hook block.
- `scripts/install_mcp.sh` registers the local `quiet_clock` MCP server with Codex.

## What Quiet Clock Never Does

Quiet Clock does not:

- Send transcript content over the network.
- Run a daemon, watcher, cron job, launch agent, or HTTP server.
- Write memory or mutate Codex transcript files.
- Contact third parties.
- Push to GitHub.

## Transcript Privacy Controls

Timeline tools default to the current thread when the caller passes the hook-injected `session/thread id`. They do not silently fall back to the latest local thread unless `allow_latest=true` is passed explicitly.

Timeline outputs support:

- `include_snippets=false` to suppress message snippets.
- `snippet_chars` to cap snippet length.
- `debug_paths=true` to include raw local transcript paths only when debugging.
