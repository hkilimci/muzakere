# Muzakere Transports

A transport is how the orchestrator reaches one external participant. Every
transport implements three operations:

```text
available()                  -> bool
open(prompt, cwd)            -> session_id
reply(session_id, prompt)    -> text
```

The command recipes below are portable starting points, not proof that a model
is reachable on a particular machine. A host must verify the command, local
authentication, required model access, and session continuation before it
admits that participant. A successful first `open()` call is the final
availability check.

## Shared rules

- Keep every participant read-only. Never bypass a sandbox or enable automatic
  write approval.
- Source the prompt from a file. If a CLI only accepts an argument, read that
  argument from the file at call time.
- Apply an external timeout to every call.
- Capture the session handle from the opening call. Never guess one or silently
  open a replacement session.
- Read only the participant's final reply, not the complete event stream.
- Never expose commands, session handles, or raw transport output to the user.
- Use the model already configured by the user unless they request another.

## codex — Codex CLI

Preflight:

```bash
command -v codex
codex --version
```

Open and continue:

```bash
codex --ask-for-approval never exec --sandbox read-only \
  --skip-git-repo-check --cd "$CWD" -o "$OUT" - < "$PROMPT"
codex --ask-for-approval never exec resume "$SESSION_ID" --skip-git-repo-check \
  -o "$OUT" - < "$PROMPT"
```

- Capture the session id printed in the opening call's run header.
- The final message is written to `$OUT` by `-o`.
- `resume` inherits the opening session configuration and accepts neither
  `--sandbox` nor `--cd`. The opening call must establish read-only access.
- `--skip-git-repo-check` allows questions outside a trusted repository.

## claude — Claude Code CLI

Preflight:

```bash
command -v claude
claude --version
command -v jq
```

Open and continue:

```bash
claude -p --permission-mode plan --permission-prompts none --output-format json \
  "$(cat "$PROMPT")" > "$OUT"
claude -p --resume "$SESSION_ID" --permission-mode plan \
  --permission-prompts none --output-format json \
  "$(cat "$PROMPT")" > "$OUT"
```

- Run the command from `$CWD`; Claude Code CLI has no `--cd` flag.
- Extract `.session_id`, `.result`, and `.is_error` with `jq`.
- Confirm that the installed Claude Code version supports the selected
  read-only permission mode before admitting the participant.

## Adding a transport

1. Confirm a non-interactive command that returns only after producing a reply.
2. Confirm how the command enforces read-only access.
3. Confirm that the opening call returns a session handle.
4. Continue that exact session and verify the handle remains stable.
5. Record exact commands, output fields, prerequisites, and version tested.

Do not admit an unverified transport. Transport failure is an Incomplete run,
not evidence that participants substantively disagree.
