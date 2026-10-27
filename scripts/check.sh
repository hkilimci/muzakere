#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/.." && pwd)"
cd "$project_root"

required_files=(
  "README.md"
  "protocol/PROTOCOL.md"
  "protocol/TRANSPORTS.md"
  "adapters/claude-code/muzakere/SKILL.md"
  "adapters/codex/muzakere/SKILL.md"
  "adapters/codex/muzakere/agents/openai.yaml"
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

for skill_file in \
  adapters/claude-code/muzakere/SKILL.md \
  adapters/codex/muzakere/SKILL.md; do
  first_name="$(awk '/^name:/{print $2; exit}' "$skill_file")"
  [[ "$first_name" == "muzakere" ]] || {
    printf 'Unexpected skill name in %s: %s\n' "$skill_file" "$first_name" >&2
    exit 1
  }
done

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
diff -qr adapters/claude-code/muzakere "$test_root/.claude/skills/muzakere" >/dev/null
diff -qr adapters/codex/muzakere "$test_root/.agents/skills/muzakere" >/dev/null

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
import subprocess
import sys

root, project = map(Path, sys.argv[1:])
targets = {
    ".agents/skills/muzakere": "adapters/codex/muzakere",
    ".claude/skills/muzakere": "adapters/claude-code/muzakere",
}
previous = {}
for relative in targets:
    skill = root / relative / "SKILL.md"
    skill.write_text(skill.read_text() + "\n<!-- Previous installation -->\n")
    previous[relative] = skill.read_bytes()
environment = dict(os.environ, MUZAKERE_INSTALL_HOME=str(root))
subprocess.run(
    [str(project / "scripts/install.sh"), "--copy", "--force", "all"],
    env=environment, stdout=subprocess.DEVNULL, check=True,
)
backups = list((root / ".muzakere-backups").rglob("SKILL.md"))
for relative, source in targets.items():
    skill = root / relative / "SKILL.md"
    assert skill.read_bytes() == (project / source / "SKILL.md").read_bytes()
    assert any(path.read_bytes() == previous[relative] for path in backups)
    assert len(list(skill.parent.parent.glob("*/SKILL.md"))) == 1
PY

printf 'All checks passed.\n'
