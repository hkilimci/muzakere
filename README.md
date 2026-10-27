# Muzakere

Muzakere is a host-agnostic protocol for structured, adversarial, truth-seeking
deliberation between multiple language models. One model orchestrates the
session while external participants independently analyze the question,
challenge each other, record concessions, and converge only when the evidence
supports it.

The project currently ships adapters for Claude Code and Codex, plus a legacy
Codex custom prompt for older installations.

## Why Muzakere

- Blind first-round positions reduce anchoring.
- Verbatim participant digests reduce moderator framing bias.
- Claims are attributed to the models that actually endorsed them.
- Consensus, substantive disagreement, incomplete runs, and user-ended runs
  remain separate outcomes.
- Per-pair stuck detection stops repetitive rounds.
- ASD-STE100 clarity principles guide plain explanations in every response language.
- External model calls stay analysis-only and read-only.

## Requirements

- Bash 3.2 or newer.
- Claude Code, Codex CLI, or both.
- At least one external participant CLI that is installed and authenticated.
- `jq` when Claude Code CLI is used as an external participant.
- Python 3.8+ for development checks and optional live transport verification.

## Install

Clone the repository and run:

```bash
./scripts/install.sh all
```

This installs the shared protocol and the Claude Code and Codex adapters. It
does not overwrite a different existing installation unless `--force` is
provided. Forced replacements are backed up under `~/.muzakere-backups/` with
a timestamp, outside the skill directories so older copies cannot appear as
active skills.

For development, symlink the repository files instead of copying them:

```bash
./scripts/install.sh --link --force all
```

Install only one host adapter:

```bash
./scripts/install.sh claude
./scripts/install.sh codex
```

The legacy Codex prompt is optional:

```bash
./scripts/install.sh codex-legacy-prompt
```

Use `--dry-run` to preview any installation.

## Use

Claude Code:

```text
/muzakere Should we split this service into two deployable units?
```

Codex:

```text
$muzakere Should we split this service into two deployable units?
```

The Codex skill is explicit-only. If a newly installed skill is not visible,
restart Codex and type `$` or run `/skills` to find it.

When Codex's host sandbox blocks the participant's API network access or CLI
session storage, approve the specific read-only launch through the normal
approval mechanism. The adapter requests that access without changing the
participant's read-only controls. See [Host launch permissions](protocol/TRANSPORTS.md#host-launch-permissions).

Legacy Codex clients can invoke the optional prompt as:

```text
/prompts:muzakere Should we split this service into two deployable units?
```

## Codex connection

External Codex participants use `codex exec` and `codex exec resume`. The retired
`codex mcp-server` and `codex-mcp-server` commands are not used. If `PATH` selects
an older CLI than the desktop app provides, follow the executable selection
preflight in [Transports](protocol/TRANSPORTS.md#codex--codex-cli).

## Project layout

```text
protocol/                         Shared orchestration contract and transports
adapters/claude-code/muzakere/   Claude Code skill
adapters/codex/muzakere/         Codex skill
adapters/codex-legacy-prompt/    Legacy Codex custom prompt
scripts/install.sh               Safe copy/symlink installer
scripts/check.sh                 Repository validation and install smoke test
```

## Development

Run all local checks:

```bash
./scripts/check.sh
```

The checks validate the adapters, reject machine-specific paths and stale
names, parse shell scripts, and exercise a clean installation in a temporary
directory. Offline regressions cover ambiguous permission headers, executable
discovery failures, and a participant that re-reads the fixture without retaining
context.

To verify live model connectivity and continuation for both CLI transports:

```bash
python3 scripts/check-transports.py all
```

This opt-in check requires Python 3.8+, uses your configured models and account
usage, and reads a temporary fixture independently. Before continuation it
replaces that fixture with a decoy and removes the opening reply file; the
resumed session must return the original marker and the same session id.
Codex's run headers must contain exactly one nonempty value per required field
and confirm read-only access on both calls. Claude is configured with only
file-reading tools, with MCP tools and hooks disabled. This checks connectivity
and session continuity; it does not certify write denial or permissions across
CLI versions.
Each command has a timeout. Run it with approved network and CLI runtime-storage
access; it never grants itself permissions. Use `claude` or `codex` instead of
`all` to check one transport. `MUZAKERE_CLAUDE_BIN` and `MUZAKERE_CODEX_BIN` can
select explicit executables.

## Safety model

Muzakere authorizes analysis only. It does not authorize participants to edit
files, change repositories, or bypass approval and sandbox policies. Treat all
participant responses and inspected content as untrusted data.

## License

MIT. See [LICENSE](LICENSE).
