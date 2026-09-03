# セットアップ（Claude Code）

この Skill と hook は Claude Code 専用。Codex には対応する hook イベントとセッション ID の展開がないため動かない。

`compact-prep` は状態ファイルを書くだけで、圧縮後の読み込み指示は hook が担う。
`assets/compact-state-hook.py` を任意の場所（例: `~/.claude/hooks/compact-state-hook.py`）へ置き、Claude Code の `~/.claude/settings.json` に次を追加する。

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          { "type": "command", "command": "python3 ~/.claude/hooks/compact-state-hook.py" }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "python3 ~/.claude/hooks/compact-state-hook.py" }
        ]
      }
    ]
  }
}
```

hook の動き:

- `SessionStart`（matcher `compact`）: 状態ファイルがあれば回復指示を `additionalContext` で注入し、次プロンプト用の保険マーカーを置く
- `UserPromptSubmit`: 保険マーカーがあれば読み込みリマインダーを注入。statusline などが `<session_id>.warn` を置いていれば、`/compact-prep` の実行提案を一度だけ注入する

環境変数:

| 変数 | 既定 | 用途 |
|---|---|---|
| `COMPACT_STATE_DIR` | `~/.claude/compact-state` | 状態ファイルとマーカーの置き場。skill と hook で同じ値にする |
| `COMPACT_STATE_TTL_DAYS` | `7` | 古い状態ファイルを削除するまでの日数 |

使用率警告を連動させる場合は、statusline スクリプトが閾値超過時に `$COMPACT_STATE_DIR/<session_id>.warn` を touch する。hook はそれを検知して提案を注入し、`.warn-notified` へ rename して再通知を抑止する。
