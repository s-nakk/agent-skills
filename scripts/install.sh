#!/usr/bin/env bash
# skills/* を agent ツールの skill ディレクトリへ symlink する
#   ~/.agents/skills : Codex が読む（他ツールとの共有先）
#   ~/.claude/skills : Claude Code が読む
# 既存の実体ディレクトリがある場合は上書きせず報告して exit 1 にする
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIRS="${AGENT_SKILLS_DIRS:-$HOME/.agents/skills:$HOME/.claude/skills}"

status=0
IFS=':' read -r -a targets <<< "$TARGET_DIRS"
for target_dir in "${targets[@]}"; do
  mkdir -p "$target_dir"
  for skill_dir in "$REPO_DIR"/skills/*/; do
    name="$(basename "$skill_dir")"
    link="$target_dir/$name"
    src="${skill_dir%/}"

    if [ -L "$link" ]; then
      current="$(readlink "$link")"
      if [ "$current" = "$src" ]; then
        echo "ok       $link (already linked)"
      else
        ln -sfn "$src" "$link"
        echo "relinked $link ($current -> $src)"
      fi
    elif [ -e "$link" ]; then
      echo "SKIP     $link is a real directory. Compare it with $src and remove it manually." >&2
      status=1
    else
      ln -s "$src" "$link"
      echo "linked   $link"
    fi
  done
done

exit $status
