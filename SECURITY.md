# Security

Quiet Clock is a local read-only Codex extension. Its security model is intentionally narrow: no network service, no daemon, no background persistence, and no write path during normal hook/MCP use.

## Threat Model

Quiet Clock can expose local Codex transcript snippets to the active Codex model when a timeline tool is called. Treat timeline output as private local context. Do not paste or forward transcript-derived output externally without review.

The main risks are accidental over-sharing from transcript snippets and accidental publication of local runtime files. The repo includes privacy and release checks to reduce those risks. Timeline tools refuse arbitrary transcript paths and only read Codex rollout JSONL files under the configured Codex sessions root.

Plugin packaging does not expand this threat model. It only points Codex at the same local hook and stdio MCP entrypoints.

## Hard Boundaries

Quiet Clock should not add:

- Network calls.
- HTTP servers.
- Daemons, cron jobs, launch agents, or watchers.
- Writes to Codex transcript/session files.
- Memory-system integrations.
- External posting, messaging, or publishing behavior.

## Reporting Issues

Report security issues privately through GitHub Security Advisories if enabled, or by opening a minimal issue that does not include secrets, local paths, or transcript content.
