#!/usr/bin/env bash
# skills/* を ~/.agents/skills/<name> へ symlink する
# Claude Code と Codex はどちらも ~/.agents/skills を読むため、1 箇所で両方に反映される
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${AGENT_SKILLS_DIR:-$HOME/.agents/skills}"

mkdir -p "$TARGET_DIR"

status=0
for skill_dir in "$REPO_DIR"/skills/*/; do
  name="$(basename "$skill_dir")"
  link="$TARGET_DIR/$name"
  src="${skill_dir%/}"

  if [ -L "$link" ]; then
    current="$(readlink "$link")"
    if [ "$current" = "$src" ]; then
      echo "ok       $name (already linked)"
    else
      ln -sfn "$src" "$link"
      echo "relinked $name ($current -> $src)"
    fi
  elif [ -e "$link" ]; then
    echo "SKIP     $name: $link is a real directory. Compare it with $src and remove it manually." >&2
    status=1
  else
    ln -s "$src" "$link"
    echo "linked   $name"
  fi
done

exit $status
