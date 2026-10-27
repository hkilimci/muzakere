---
name: muzakere
description: Explicitly run a structured, adversarial, truth-seeking multi-model deliberation to answer a bounded question or resolve a decision.
---

# Muzakere — Codex adapter

Read `~/.muzakere/PROTOCOL.md` and `~/.muzakere/TRANSPORTS.md` completely, then
run that protocol. This adapter only binds the shared protocol to Codex. If
either file is missing, stop and report the missing file; do not improvise the
protocol.

## Bindings

- `ARGS` = the user's request following the explicit `$muzakere` invocation.
- **Host** = Codex. This model is the ORCHESTRATOR.
- `PARTICIPANTS` = every runtime-verified transport in `TRANSPORTS.md` except
  `codex`, unless the user named specific participants. Verify availability
  before admitting each participant; drop and report unavailable ones.
- `HOST_IS_PARTICIPANT` = the protocol default: true with one external
  participant and false with two or more, unless the user requests a mode.
- `ask_user(question, options)` = use the structured user-input tool when one
  is available. Otherwise print the question and numbered options, then stop
  for the user's response.
- `scratch_dir` = a fresh directory created with `mktemp -d`.

## Host notes

- Use shell access to launch participant CLIs. Every participant call must use
  the read-only posture defined in `TRANSPORTS.md`.
- Follow the Host launch permissions section in `TRANSPORTS.md`. If the current
  sandbox blocks API networking or CLI session storage, request launch access
  through the normal shell approval mechanism and retry the same read-only
  command. Keep the participant's permission controls unchanged. If approval
  is denied or unavailable, report the specific transport failure.
- Verify opening and continuation before admitting a participant. CLI presence
  and authentication alone do not prove that a model call can complete.
- Never present a blocked launch as substantive disagreement.
- Never grant a participant write access or bypass its approval controls.
