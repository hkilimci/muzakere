# Muzakere — Codex CLI adapter

Read `~/.muzakere/PROTOCOL.md` and `~/.muzakere/TRANSPORTS.md` now, then run that protocol. This file only binds it to this host; it does not restate it. If either file is missing, stop and say so — do not improvise the protocol.

## Bindings

- `ARGS` = `$ARGUMENTS`
- **Host** = Codex CLI. This model is the ORCHESTRATOR.
- `PARTICIPANTS` = every verified transport in TRANSPORTS.md except `codex`, unless the user named specific ones in `$ARGUMENTS`. Check `available()` for each before admitting it; drop and report the ones that fail.
- `HOST_IS_PARTICIPANT` = protocol default (true with one external participant, false with two or more), unless the user asked for one mode.
- `ask_user(question, options)` = **no structured tool here.** Print the question, then the options as a numbered list, then STOP and wait for the user's next message. Never pick an option yourself.
- `scratch_dir` = `mktemp -d`.

## Host notes

- Running this protocol requires shell access to launch participant CLIs. If the current sandbox forbids running `claude` or `opencode`, say so and stop — do not report a blocked launch as a participant disagreement.
- Participant calls are read-only analysis calls, but they are still process launches: if approvals are on, expect one prompt per call.
