---
name: muzakere
description: Run a structured, adversarial, truth-seeking muzakere between this model and one or more external LLMs to answer a question or resolve a decision.
argument-hint: "[question or decision]"
disable-model-invocation: true
allowed-tools: Bash Read Grep Glob AskUserQuestion WebSearch WebFetch mcp__codex__codex mcp__codex__codex-reply
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

## Transport preference

If the `codex` MCP server is connected, prefer `mcp__codex__codex` / `mcp__codex__codex-reply` for the `codex` participant (`sandbox: read-only`, `approval-policy: never`, `cwd` from Phase 0, the user's configured model). On failure retry once, then fall back to the `codex` CLI transport. Tell the user in one line which transport is in use and why. Never switch silently.

All other participants use their CLI transport via `Bash`, with a timeout on every call.
