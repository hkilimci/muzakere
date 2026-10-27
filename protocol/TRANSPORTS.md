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

- Keep every participant read-only. Never disable its permission controls or
  sandbox, or enable automatic write approval.
- Source the prompt from a file. If a CLI only accepts an argument, read that
  argument from the file at call time.
- Apply an external timeout to every call.
- Capture the session handle from the opening call. Never guess one or silently
  open a replacement session.
- Read only the participant's final reply, not the complete event stream.
- Never expose commands, session handles, or raw transport output to the user.
- Use the model already configured by the user unless they request another.

## Host launch permissions

The launcher needs API network access and the selected CLI's normal runtime
storage for authentication, caches, and resumable sessions. Read-only
participant tools do not remove those requirements. Do not redirect `HOME`,
`CODEX_HOME`, or `CLAUDE_CONFIG_DIR` to an empty directory to work around them:
that can select a different login, model, or session store.

If a host sandbox blocks DNS, API access, or runtime storage, request the
necessary launch access through that host's normal approval mechanism, then
retry the same read-only command. In Codex, this can require an approved
`require_escalated` shell call. Approval for the launcher does not grant the
participant permission to edit project files: retain every read-only and
approval-denial flag below on both opening and continuation. Never use a
participant's bypass-permissions or full-access flags as a recovery step.

If launch access is denied or unavailable, report the specific transport
failure and stop that participant. An installed CLI or successful auth-status
check does not prove model connectivity. A timeout with no output is not
evidence of missing model access.

Verified failure pattern on 2026-10-27: a Codex host with restricted networking
and home-directory writes timed out calling Claude, while diagnostics reported
`getaddrinfo ENOTFOUND api.anthropic.com` and `EPERM` on Claude session storage.
The same plan-mode command opened and resumed successfully after approved
launch access; no participant permission controls were disabled.

## codex — Codex CLI

Preflight:

```bash
CODEX_BIN="${MUZAKERE_CODEX_BIN:-$(command -v codex)}"
"$CODEX_BIN" --version
```

Set `MUZAKERE_CODEX_BIN` to select a particular executable. Otherwise compare the
standalone and desktop-bundled versions when both are present, and use the newer
verified CLI for both calls. On macOS a desktop-bundled CLI may be available at
`/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`; check that it
exists and verify its version before selecting it:

```bash
CODEX_BIN="/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex"
"$CODEX_BIN" --version
```

Keep the configured model. A stale model cache alone does not establish missing
account access; check the actual client version and model connectivity before
changing the model.

The removed `codex mcp-server` / `codex-mcp-server` transport is unavailable.
Do not substitute `codex app-server` into an MCP client; it uses another protocol.

Open and continue:

```bash
"$CODEX_BIN" --ask-for-approval never exec --sandbox read-only \
  --skip-git-repo-check --cd "$CWD" -o "$OUT" - < "$PROMPT"
"$CODEX_BIN" -c sandbox_mode='"read-only"' --ask-for-approval never \
  exec --cd "$CWD" resume "$SESSION_ID" --skip-git-repo-check -o "$OUT" - < "$PROMPT"
```

- Capture the session id printed in the opening call's run header.
- The final message is written to `$OUT` by `-o`.
- `--sandbox` and `--cd` are parent `exec` options: put them before `resume`,
  not after it. Continuation does NOT reliably inherit the opening sandbox:
  codex-cli 0.162.0-alpha.17.2 resumed with `sandbox: workspace-write`
  (verified 2026-10-14). Always pass the global
  `-c sandbox_mode='"read-only"'` override on continuation. Explicitly set
  `--ask-for-approval never` and `--cd "$CWD"` on both calls; use the same binary.
- Before using a reply, inspect only the run header's permission, workdir, and
  session fields: require `sandbox: read-only`, `approval: never`, and workdir
  equal to `$CWD` after resolving symlinks. Missing or conflicting metadata is
  a transport failure; discard the reply and never retry with broader access.
- On continuation, require the returned session id to equal `$SESSION_ID`.
  Some versions silently start a new session if the requested id is missing;
  reject that replacement as a transport failure.
- Before first use, or after changing the executable version or command recipe,
  verify both opening and continuation in a disposable scratch directory: a
  harmless read must succeed and a harmless write must be denied in each call.
  Never probe writes on project files. Help output alone is insufficient.
  If permission verification cannot complete, report the transport unavailable.
- `--skip-git-repo-check` allows questions outside a trusted repository.

## claude — Claude Code CLI

Preflight:

```bash
CLAUDE_BIN="${MUZAKERE_CLAUDE_BIN:-$(command -v claude)}"
"$CLAUDE_BIN" --version
command -v jq
```

Open and continue:

```bash
"$CLAUDE_BIN" -p --permission-mode plan --permission-prompts none --output-format json \
  --tools 'Read,Grep,Glob' --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --settings '{"disableAllHooks":true}' \
  "$(cat "$PROMPT")" > "$OUT"
"$CLAUDE_BIN" -p --resume "$SESSION_ID" --permission-mode plan \
  --permission-prompts none --output-format json \
  --tools 'Read,Grep,Glob' --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --settings '{"disableAllHooks":true}' \
  "$(cat "$PROMPT")" > "$OUT"
```

- Run the command from `$CWD`; Claude Code CLI has no `--cd` flag.
- Extract `.session_id`, `.result`, and `.is_error` with `jq`.
- Require a successful exit, `.is_error == false`, a nonempty `.result`, and a
  nonempty `.session_id`. On continuation the returned id must equal the
  opening id; reject a replacement session.
- Confirm that the installed Claude Code version supports the selected
  read-only permission mode and tool/config flags before admitting the
  participant. File-reading tools are the only participant tools exposed;
  shell, editing, MCP tools, and custom hooks are excluded. The orchestrator
  supplies external evidence that these tools cannot reach.
- Keep the same verified executable and working directory for both calls.
  Allow the CLI's own session bookkeeping so `--resume` can find the opening
  session. Do not use `--no-session-persistence` for this transport.

## Adding a transport

1. Confirm a non-interactive command that returns only after producing a reply.
2. Confirm how the command enforces read-only access.
3. Confirm that the opening call returns a session handle.
4. Continue that exact session and verify the handle remains stable.
5. Record exact commands, output fields, prerequisites, and version tested.

Do not admit an unverified transport. Transport failure is an Incomplete run,
not evidence that participants substantively disagree.
