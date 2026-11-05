---
name: muzakere
description: Explicitly run a structured, adversarial, truth-seeking muzakere between this model and one or more external LLMs to answer a bounded question or resolve a decision.
argument-hint: "[question or decision]"
disable-model-invocation: true
allowed-tools: Bash Read Grep Glob AskUserQuestion WebSearch WebFetch
---

# Muzakere — shared agent skill

Read `~/.muzakere/PROTOCOL.md` and `~/.muzakere/TRANSPORTS.md` completely, then
run that protocol. This skill only binds the shared protocol to the host that
loaded it; it does not restate it. If either file is missing, stop and report
the missing file; do not improvise the protocol.

One copy of this skill serves every host. Claude Code, Codex, and other agent
CLIs that read `~/.agents/skills` load the same file.

## Bindings

- `ARGS` = the text the user gave with the explicit invocation
  (`/muzakere …` in Claude Code, `$muzakere …` in Codex).
- **Host** = the agent CLI running this skill. This model is the ORCHESTRATOR.
- `PARTICIPANTS` = every runtime-verified transport in `TRANSPORTS.md` except
  the host's own (`claude` in Claude Code, `codex` in Codex), unless the user
  named specific participants (e.g. "codex ile", "codex ve opencode ile").
  Verify availability before admitting each participant; drop and report
  unavailable ones.
- `HOST_IS_PARTICIPANT` = the protocol default: true with one external
  participant and false with two or more, unless the user requests a mode.
- `ask_user(question, options)` = the host's structured question tool when it
  has one (`AskUserQuestion` in Claude Code). Otherwise print the question and
  numbered options, then stop for the user's response. Never pick an option
  yourself.
- `scratch_dir` = the host session's scratchpad directory when it has one;
  otherwise a fresh directory created with `mktemp -d`.
- `RENDERING` = tables yes. Mermaid unknown: terminal drawing of Mermaid fences
  depends on optional, version-specific client features, so use Mermaid only
  when the user asks for it.

## Codex participant

Use the `codex` CLI transport in `TRANSPORTS.md`. The `codex mcp-server`
command and standalone `codex-mcp-server` binary have been removed. Do not call
the retired Codex MCP tools or retry that transport. The Codex app server is
not an MCP replacement.

Resolve and verify the actual Codex executable before Phase 0 using the
preflight in `TRANSPORTS.md`. Honor an explicit executable selection; otherwise
prefer the newer verified CLI when standalone and desktop versions differ.
Use that same executable for opening and continuing the participant session.
Keep the user's configured model unless they request a change. A stale model
cache or an old client alone does not establish that the account lacks access.
Verify model connectivity before doing extensive factual preparation. On
failure report the exact executable version and error category.

## Host notes

- Use shell access to launch participant CLIs. Every participant call must use
  the read-only posture defined in `TRANSPORTS.md`: disable write approvals,
  source prompts from files, and apply an external timeout to every call.
- Follow the Host launch permissions section in `TRANSPORTS.md`. If the current
  sandbox blocks API networking or CLI session storage, request launch access
  through the normal approval mechanism and retry the same read-only command.
  Keep the participant's permission controls unchanged. If approval is denied
  or unavailable, report the specific transport failure.
- Verify opening and continuation before admitting a participant. CLI presence
  and authentication alone do not prove that a model call can complete.
- State the chosen transport and executable version in one short line.
- Never present a blocked launch as substantive disagreement.
- Never grant a participant write access or bypass its approval controls.
