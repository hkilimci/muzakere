#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/.." && pwd)"
install_root="${MUZAKERE_INSTALL_HOME:-$HOME}"
install_mode="copy"
force="false"
dry_run="false"
target="all"
timestamp="$(date +%Y%m%d%H%M%S)"

usage() {
  printf '%s\n' \
    'Usage: ./scripts/install.sh [--copy|--link] [--force] [--dry-run] [target]' \
    '' \
    'Targets:' \
    '  all                   Shared protocol, Claude Code, and Codex skill' \
    '  claude                Shared protocol and Claude Code skill' \
    '  codex                 Shared protocol and Codex skill' \
    '  codex-legacy-prompt   Shared protocol and legacy Codex prompt' \
    '' \
    'Environment:' \
    '  MUZAKERE_INSTALL_HOME Override the destination home directory for testing.'
}

while (($#)); do
  case "$1" in
    --copy) install_mode="copy" ;;
    --link) install_mode="link" ;;
    --force) force="true" ;;
    --dry-run) dry_run="true" ;;
    -h|--help) usage; exit 0 ;;
    all|claude|codex|codex-legacy-prompt) target="$1" ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

sources=("$project_root/protocol")
destinations=("$install_root/.muzakere")

case "$target" in
  all)
    sources+=(
      "$project_root/adapters/claude-code/muzakere"
      "$project_root/adapters/codex/muzakere"
    )
    destinations+=(
      "$install_root/.claude/skills/muzakere"
      "$install_root/.agents/skills/muzakere"
    )
    ;;
  claude)
    sources+=("$project_root/adapters/claude-code/muzakere")
    destinations+=("$install_root/.claude/skills/muzakere")
    ;;
  codex)
    sources+=("$project_root/adapters/codex/muzakere")
    destinations+=("$install_root/.agents/skills/muzakere")
    ;;
  codex-legacy-prompt)
    sources+=("$project_root/adapters/codex-legacy-prompt/muzakere.md")
    destinations+=("$install_root/.codex/prompts/muzakere.md")
    ;;
esac

is_current() {
  local source_path="$1"
  local destination_path="$2"

  if [[ "$install_mode" == "link" ]]; then
    [[ -L "$destination_path" && "$(readlink "$destination_path")" == "$source_path" ]]
  elif [[ -d "$source_path" && -d "$destination_path" ]]; then
    diff -qr "$source_path" "$destination_path" >/dev/null
  elif [[ -f "$source_path" && -f "$destination_path" ]]; then
    cmp -s "$source_path" "$destination_path"
  else
    return 1
  fi
}

for index in "${!sources[@]}"; do
  source_path="${sources[$index]}"
  destination_path="${destinations[$index]}"

  if [[ ! -e "$source_path" ]]; then
    printf 'Missing project source: %s\n' "$source_path" >&2
    exit 1
  fi

  if [[ -e "$destination_path" || -L "$destination_path" ]]; then
    if is_current "$source_path" "$destination_path"; then
      continue
    fi
    if [[ "$force" != "true" ]]; then
      printf 'Refusing to replace existing path: %s\n' "$destination_path" >&2
      printf 'Re-run with --force to back it up and continue.\n' >&2
      exit 1
    fi
  fi
done

for index in "${!sources[@]}"; do
  source_path="${sources[$index]}"
  destination_path="${destinations[$index]}"

  if [[ -e "$destination_path" || -L "$destination_path" ]]; then
    if is_current "$source_path" "$destination_path"; then
      printf 'Unchanged: %s\n' "$destination_path"
      continue
    fi
    backup_path="${destination_path}.bak.${timestamp}"
    backup_suffix=1
    while [[ -e "$backup_path" || -L "$backup_path" ]]; do
      backup_path="${destination_path}.bak.${timestamp}.${backup_suffix}"
      backup_suffix=$((backup_suffix + 1))
    done
    printf 'Backup: %s -> %s\n' "$destination_path" "$backup_path"
    if [[ "$dry_run" != "true" ]]; then
      mv -- "$destination_path" "$backup_path"
    fi
  fi

  printf 'Install (%s): %s -> %s\n' "$install_mode" "$source_path" "$destination_path"
  if [[ "$dry_run" == "true" ]]; then
    continue
  fi

  mkdir -p -- "$(dirname -- "$destination_path")"
  if [[ "$install_mode" == "link" ]]; then
    ln -s -- "$source_path" "$destination_path"
  elif [[ -d "$source_path" ]]; then
    cp -R -- "$source_path" "$destination_path"
  else
    cp -- "$source_path" "$destination_path"
  fi
done

printf 'Muzakere installation complete for target: %s\n' "$target"
