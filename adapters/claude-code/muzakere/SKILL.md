---
name: muzakere
description: Run a structured, adversarial, truth-seeking muzakere between this model and one or more external LLMs to answer a question or resolve a decision.
argument-hint: "[question or decision]"
disable-model-invocation: true
allowed-tools: Bash Read Grep Glob AskUserQuestion WebSearch WebFetch
---

# Muzakere — Claude Code adapter

Read `~/.muzakere/PROTOCOL.md` and `~/.muzakere/TRANSPORTS.md` now, then run that protocol. This file only binds it to this host; it does not restate it. If either file is missing, stop and say so — do not improvise the protocol.

## Bindings

- `ARGS` = `$ARGUMENTS`
- **Host** = Claude Code. This model is the ORCHESTRATOR.
- `PARTICIPANTS` = every verified transport in TRANSPORTS.md except `claude`, unless the user named specific ones in `$ARGUMENTS` (e.g. "codex ile", "codex ve opencode ile"). Check `available()` for each before admitting it; drop and report the ones that fail.
- `HOST_IS_PARTICIPANT` = protocol default (true with one external participant, false with two or more), unless the user asked for one mode.
- `ask_user(question, options)` = the `AskUserQuestion` tool.
- `scratch_dir` = this session's scratchpad directory; fall back to `mktemp -d` if there is none.

## Codex transport

Use the `codex` CLI transport in `~/.muzakere/TRANSPORTS.md`.
The `codex mcp-server` command and standalone `codex-mcp-server` binary have
been removed. Do not call the retired Codex MCP tools or retry that transport.
The Codex app server is not an MCP replacement.

Resolve and verify the actual Codex executable before Phase 0 using the
preflight in `TRANSPORTS.md`. Honor an explicit executable selection; otherwise
prefer the newer verified CLI when standalone and desktop versions differ.
Use that same executable for opening and continuing the participant session.
Keep the user's configured model unless they request a change. A stale model
cache or an old client alone does not establish that the account lacks access.
Verify model connectivity before doing extensive factual preparation. On
failure report the exact executable version and error category.

Keep every participant read-only, disable write approvals, source prompts from
files, and apply an external timeout to every call. State the chosen transport
and executable version in one short line. Other participants use their CLI
transports as defined in `TRANSPORTS.md`.
