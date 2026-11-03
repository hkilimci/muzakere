#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/.." && pwd)"
cd "$project_root"

required_files=(
  "README.md"
  "protocol/PROTOCOL.md"
  "protocol/TRANSPORTS.md"
  "adapters/agents/muzakere/SKILL.md"
  "adapters/agents/muzakere/agents/openai.yaml"
  "adapters/codex-legacy-prompt/muzakere.md"
  "scripts/install.sh"
  "scripts/check-transports.py"
  "scripts/test_check_transports.py"
  "scripts/fixtures/codex-0.164.header.txt"
)

for required_file in "${required_files[@]}"; do
  [[ -f "$required_file" ]] || { printf 'Missing: %s\n' "$required_file" >&2; exit 1; }
done

bash -n scripts/install.sh scripts/check.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts -p 'test_*.py'

skill_file="adapters/agents/muzakere/SKILL.md"
first_name="$(awk '/^name:/{print $2; exit}' "$skill_file")"
[[ "$first_name" == "muzakere" ]] || {
  printf 'Unexpected skill name in %s: %s\n' "$skill_file" "$first_name" >&2
  exit 1
}

legacy_name="$(printf '%s%s' 'de' 'bate')"
if grep -RIni --exclude-dir=.git --exclude=check.sh "$legacy_name" .; then
  printf 'Found a stale project name.\n' >&2
  exit 1
fi

if grep -RIn --exclude-dir=.git --exclude=check.sh '/Users/' .; then
  printf 'Found a machine-specific path.\n' >&2
  exit 1
fi

test_root="$(mktemp -d)"
trap 'rm -rf -- "$test_root"' EXIT

MUZAKERE_INSTALL_HOME="$test_root" ./scripts/install.sh --copy all >/dev/null
diff -qr protocol "$test_root/.muzakere" >/dev/null
diff -qr adapters/agents/muzakere "$test_root/.agents/skills/muzakere" >/dev/null
[[ "$(readlink "$test_root/.claude/skills/muzakere")" == "../../.agents/skills/muzakere" ]] || {
  printf 'Claude Code skill is not a link to the shared skill.\n' >&2
  exit 1
}
diff -qr adapters/agents/muzakere "$test_root/.claude/skills/muzakere/" >/dev/null

link_root="$test_root/link-home"
MUZAKERE_INSTALL_HOME="$link_root" ./scripts/install.sh --link all >/dev/null
[[ "$(readlink "$link_root/.muzakere")" == "$project_root/protocol" &&
   "$(readlink "$link_root/.agents/skills/muzakere")" == "$project_root/adapters/agents/muzakere" &&
   "$(readlink "$link_root/.claude/skills/muzakere")" == "../../.agents/skills/muzakere" ]] || {
  printf 'Link install does not point every host at the project.\n' >&2
  exit 1
}
cmp -s adapters/agents/muzakere/SKILL.md "$link_root/.claude/skills/muzakere/SKILL.md"

MUZAKERE_INSTALL_HOME="$test_root" \
  ./scripts/install.sh --copy codex-legacy-prompt >/dev/null
cmp -s \
  adapters/codex-legacy-prompt/muzakere.md \
  "$test_root/.codex/prompts/muzakere.md"

second_install_output="$(MUZAKERE_INSTALL_HOME="$test_root" ./scripts/install.sh --copy all)"
case "$second_install_output" in
  *Unchanged:*) ;;
  *) printf 'Idempotent install check failed.\n' >&2; exit 1 ;;
esac

python3 - "$test_root" "$project_root" <<'PY'
import os
from pathlib import Path
import shutil
import subprocess
import sys

root, project = map(Path, sys.argv[1:])
shared = root / ".agents/skills/muzakere"
claude = root / ".claude/skills/muzakere"
# Simulate an older per-host install: an edited shared copy and a separate
# Claude Code copy instead of the link.
claude.unlink()
shutil.copytree(shared, claude)
previous = {}
for path in (shared, claude):
    skill = path / "SKILL.md"
    skill.write_text(skill.read_text() + f"\n<!-- Previous {path.parent.parent.name} -->\n")
    previous[path] = skill.read_bytes()
environment = dict(os.environ, MUZAKERE_INSTALL_HOME=str(root))
subprocess.run(
    [str(project / "scripts/install.sh"), "--copy", "--force", "all"],
    env=environment, stdout=subprocess.DEVNULL, check=True,
)
backups = list((root / ".muzakere-backups").rglob("SKILL.md"))
assert claude.is_symlink() and os.readlink(claude) == "../../.agents/skills/muzakere"
source = (project / "adapters/agents/muzakere/SKILL.md").read_bytes()
for path in (shared, claude):
    assert (path / "SKILL.md").read_bytes() == source
    assert any(backup.read_bytes() == previous[path] for backup in backups)
    assert len(list(path.parent.glob("*/SKILL.md"))) == 1
PY

printf 'All checks passed.\n'
