# Windows と Mac への導入

この Skill の本体は Markdown・YAML だけで構成する。規約の導入に Bash、PowerShell スクリプト、シンボリックリンク、管理者権限は必要ない。製品の開発ツールや、選択する他の Skill の対応 OS は別途確認する。

## GitHub から直接導入する

導入先の Windows / Mac で Node.js（npm / npx）と Git を利用できる場合は、次を実行する。端末間で ZIP を受け渡す必要はない。

```sh
npx skills add s-nakk/agent-skills --skill setup-development-policy --agent codex --global --copy
```

Windows PowerShell で `npx.ps1` が実行ポリシーにより止まる場合は、先頭を `npx.cmd` にする。Claude Code へ入れる場合は `--agent claude-code` を使う。新しいセッションで Skill を確認する。既存の同名 Skill があれば独自変更を比較してから更新する。[CLI の公式 README](https://github.com/vercel-labs/skills) に取得元・対象ツール・コピー方式の指定を確認できる。

## 手動で配置する場合

ZIP を展開し、`SKILL.md`・`agents`・`assets`・`references` を含む `setup-development-policy` フォルダー全体を、使用するツールの Skill 保存先へコピーする。リポジトリの ZIP なら `skills/setup-development-policy` を取り出す。`SKILL.md` だけをコピーせず、同名フォルダーを二重に入れない。

標準のユーザー単位の保存先は次のとおり。既存インストールや管理設定がある場合は、対象ツールが実際に読む場所を確認し、同じ Skill を複数箇所へ追加しない。

| ツール | macOS（Finder の「フォルダへ移動」） | Windows ネイティブ（エクスプローラーのアドレス欄） |
|---|---|---|
| Codex | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` |
| Claude Code | `~/.claude/skills/` | `%USERPROFILE%\.claude\skills\` |

保存先がなければフォルダーを作る。配置後は `<保存先>/setup-development-policy/SKILL.md` と参照ファイルが存在することを確認し、対象ツールで新しいセッションを開いて Skill を確認する。ユーザー設定で別の読み込み先を使っている場合はその設定に従う。

同名の既存フォルダーがある場合は新旧を比較して更新する。独自変更を一括上書きしない。コピー方式では配布元を更新しても自動反映されないため、更新版を同じ保存先へ反映する。規約を導入した各プロジェクトの更新は、その後でこの Skill に依頼する。

保存先の一次資料: [Codex の Skills](https://developers.openai.com/codex/skills/)、[Claude Code の Skills](https://code.claude.com/docs/en/skills)。対応アプリ・版の設定が異なる場合は現物を優先する。

## プロジェクト規約の移植

- プロジェクト内の `.agent-policy/core.md`・`project.md` と有効な入口を共有する。参照はルート基準の相対パスと `/` に統一する。実ファイルと文字の大小を合わせる
- 確定済みの運用は維持し、OS・シェル・ツールで実行不能な項目だけ見直す。Windows だから Issue を必須にするなど、環境と無関係な運用変更をしない
- `package.json` の scripts など共通の入口があっても、内部が `bash`、`export`、POSIX コマンドなどへ依存していないか確認する。別 OS で未実行なら、その環境は未確認と記録する。実装の移植が必要なら今回の規約整備の範囲と区別する
- PowerShell と Bash / zsh では環境変数、引用、コマンド連結が異なる。共有コマンドを優先し、必要な場合だけ OS とシェル別の実在する手順を保存する。空白や日本語を含むパスを引用し、UTF-8 の文書を維持する。既存ファイルの改行を無関係に全面変換しない
- ホーム・一時ファイル・作業ツリーの絶対パスは実行時に解決する。GLOBAL も依頼された場合は、そのツールの設定ディレクトリを基準に配置と参照を組み立てる。移植元の絶対パスや端末の設定一式をコピーせず、認証情報を含めない
- Windows 上でも agent が WSL で動く場合は、WSL 側のホーム・シェル・Skill 保存先を確認する。Windows の保存先やパスをそのまま使えると仮定せず、WSL の導入自体も必須にしない
