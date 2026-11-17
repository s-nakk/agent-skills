#!/usr/bin/env bash
# independent-review profile で Codex reviewer を起動・再開する
#
# 初回:   run-codex-review.sh [codex exec の option...] '<prompt>'
# 再開:   run-codex-review.sh resume <reviewer-session-id> '<prompt>'
#
# -p independent-review は常に resume より前に置かれる（resume は -p を受け付けず、語順を誤ると read-only が外れる）
#
# Windows の elevated sandbox はコマンドを専用のローカルユーザーで実行するため、呼び出し元ユーザーの
# 資格情報マネージャー（gh の keyring）を読めず、gh が HTTP 401 になる。呼び出し元の token を GH_TOKEN で渡す。
# token はこのプロセスの環境変数にだけ置き、ファイルや config には書かない
set -euo pipefail

if ! GH_TOKEN="$(gh auth token)"; then
  echo "run-codex-review: gh auth token failed; run 'gh auth login' as the calling user first" >&2
  exit 1
fi
export GH_TOKEN

exec codex exec -p independent-review "$@" < /dev/null
