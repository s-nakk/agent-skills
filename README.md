# agent-skills

Claude Code と Codex の両方で使う、開発フロー用の自作 Skill 集（`compact-prep` だけは Claude Code 専用）。
プロジェクト固有の情報は本文から外し、実例だけを各 Skill の `references/examples.md` に匿名化して残している。

## Skill 一覧

| Skill | 役割 | 主な依存 |
|---|---|---|
| [`setup-development-policy`](skills/setup-development-policy/SKILL.md) | 既存規約を調べ、Issue・設計承認・Git・Worktree・独立レビュー・保存範囲を初回だけ対話で決める。GLOBAL と Project の AGENTS.md・補助規約を役割別に展開する（Codex 向け） | なし（対話ツールがなければ通常の会話） |
| [`independent-final-review`](skills/independent-final-review/SKILL.md) | 実装者から独立した reviewer セッションで、PR や commit 差分を read-only のリスク重み付き敵対的検証にかける。再レビューは同じ reviewer を再開する | Codex: `assets/independent-review.config.toml` の profile。Claude Code: subagent |
| [`change-design-gate`](skills/change-design-gate/SKILL.md) | 変更に着手する前に、処理パイプライン図・具体例・受け入れ条件・テストケースを含む自己完結 HTML を作り、明示承認まで実装を止める | `gh`、`assets/` の HTML と台帳の雛形 |
| [`github-issue-flow`](skills/github-issue-flow/SKILL.md) | GitHub Issue を起点に、既存 Issue を変更せず worktree 分離・SDD/TDD・検証・draft PR・独立レビューまで進める定型フロー | `gh` |
| [`thermo-nuclear-code-quality-review`](skills/thermo-nuclear-code-quality-review/SKILL.md) | 抽象化の質、巨大ファイル化、条件分岐の増殖を極めて厳しく審査する保守性レビュー | なし |
| [`compact-prep`](skills/compact-prep/SKILL.md) | コンテキスト圧縮の前に、採用・却下した判断と次の一手を状態ファイルへ退避する。**Claude Code 専用** | `assets/compact-state-hook.py` を hook 登録（`references/setup.md`） |
| [`explained-diff-review`](skills/explained-diff-review/SKILL.md) | 実装完了後に、変更を画面 → API → アプリケーション → 永続化の順に並べた説明付きレビュー画面を会話内に表示する。影響範囲マップ、2 列差分、グループ単位の承認とコメント、差分の行に差し込む行コメント、スナップショット ID による承認の同一性検証を含む。差分にはファイルごとの見出し（概要と「エディタで開く」リンク、`--editor` で URL スキームを選択）と、hunk の該当行の直下に差し込む解説（`hunk_notes`、行アンカー対応）を置ける。対になる削除行と追加行では実際に変わったトークンだけを行内で強調する。承認の単位はファイルで、各ファイル見出しのチェックとグループ単位の一括チェックがあり、payload は `approved_files` を運ぶ。画面の言語は生成時に `locale` で日本語 / 英語を選ぶ。会話内の幅が足りない時は `--layout page` で、左にマップとグループ一覧、右に説明と差分を置く 2 ペインの単独 HTML を生成できる（送信はメッセージのコピー & 貼り付け） | Python 3、`git`。Claude Code: `visualize` MCP の `show_widget`。Codex: 同梱 `visualize` skill |

初回は `setup-development-policy` でプロジェクトの運用を選択する。Issue なし・ローカル完了も選べるため、以下のフローは全プロジェクトへの必須条件ではない。

Issue と設計ゲートを採用した場合の組み合わせ: `github-issue-flow` で Issue を確定 → `change-design-gate` で設計承認 → 実装 → draft PR → `independent-final-review`。`thermo-nuclear-code-quality-review` は保守性を別軸で見たい時に追加で使う。`explained-diff-review` は実装と独立レビューが終わった変更をユーザーが会話内で確認・承認する時に使う。

## 導入

### skills CLI（推奨）

Windows / Mac ともに、導入先の端末で直接取得する。Node.js（npm / npx）と Git が必要。

開発方針の導入用 Skill だけを Codex のユーザー領域へ入れる場合:

```sh
npx skills add s-nakk/agent-skills --skill setup-development-policy --agent codex --global --copy
```

`--copy` によりシンボリックリンクを使わず取得できる。Windows PowerShell で `npx.ps1` の実行が制限される場合は、先頭を `npx.cmd` にする。この Skill の展開対象は Codex の規約。既存の同名 Skill がある場合は、更新前に独自変更を比較する。

他の Skill も選んで導入する場合:

```bash
npx skills add s-nakk/agent-skills
```

CLI のオプションは [skills の公式 README](https://github.com/vercel-labs/skills) を参照する。

### clone + symlink（macOS / Bash 環境）

Codex は `~/.agents/skills` を、Claude Code は `~/.claude/skills` を読む。`scripts/install.sh` は両方へ symlink を張るので、`git pull` 1 回で両ツールに反映される。

```bash
git clone https://github.com/s-nakk/agent-skills.git ~/projects/agent-skills
~/projects/agent-skills/scripts/install.sh
```

`scripts/install.sh` は `skills/*` を `~/.agents/skills/<name>` と `~/.claude/skills/<name>` へ symlink する。対象は `AGENT_SKILLS_DIRS`（`:` 区切り）で変えられる。既存の実体ディレクトリがある場合はそれを飛ばして報告し、最後に exit 1 を返す。

### フォルダーコピー（手動導入が必要な場合）

`setup-development-policy` はスクリプト実行なしで導入できる。GitHub の「Code → Download ZIP」で取得・展開し、`skills/setup-development-policy` フォルダー全体をコピーする。単独配布 ZIP なら、その中の同名フォルダーを使う。

| ツール | Mac | Windows ネイティブ |
|---|---|---|
| Codex | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` |
| Claude Code | `~/.claude/skills/` | `%USERPROFILE%\.claude\skills\` |

コピー先の `setup-development-policy/SKILL.md` を確認し、新しいセッションで Skill を読み込む。既存の同名 Skill がある場合は差分を比較し、独自変更を保持して更新する。コピー方式は `git pull` で自動更新されない。Windows では `install.sh`、WSL、管理者権限を必須にしない。

詳細は [Windows と Mac への導入](skills/setup-development-policy/references/platforms.md) を参照する。この対応範囲は導入用 Skill と共通規約であり、他の Skill のスクリプトや各プロジェクトのビルドの OS 対応は、それぞれ確認する。

### GLOBAL と Project の規約を導入する

インストール後、対象プロジェクトの Codex で次を依頼する。

```text
$setup-development-policy で、GLOBAL とこのプロジェクトに開発ルールを展開して。
既存ルールを保持し、Issue など未確定の運用だけ質問して。
```

元の GLOBAL と基準プロジェクトの規約から固有情報を除いた原本を、その役割のまま使う。新たな共通規約を生成して両方へコピーする方式ではない。

| 展開先 | 内容 |
|---|---|
| Codex 設定先の `AGENTS.md` と `rule-reference/coding.md` | 応答・調査・コーディング・品質・サブエージェントの共通方針 |
| Project の `AGENTS.md` と `.codex/rule-reference/` | 作業フロー・独立レビュー・運用選択・導入先の正本と追加条件 |

Codex 設定先は `CODEX_HOME`、未設定ならユーザーホームの `.codex`。Windows / Mac ともに実際のホームを解決する。GLOBAL に Project の参照を入れず、Project に GLOBAL の共通本文を再掲しない。業務専用の契約、技術スタック、CI の固定値、元端末のパスや認証情報は配布しない。[原本・配置・除外対象](skills/setup-development-policy/references/template-map.md) に対応をまとめている。

「GLOBAL のみ」「Project のみ」も指定できる。Project のみの場合は必要な GLOBAL が有効かを確認し、不足すれば具体的な追加案を示す。Issue などの確定済み選択は再質問せず、保存した運用に応じて手順を適用する。

Skill の更新と、展開済み規約の更新は別操作。更新を依頼した時だけ原本と既存本文を比較し、独自条件と運用選択を保持する。v1 の `.agent-policy/` も、GLOBAL と Project へ役割を分けて引き継ぐ。導入先の回答や固有情報をこの配布リポジトリへ送信しない。

### Skill ごとの追加設定

- `independent-final-review`（Codex）: `skills/independent-final-review/assets/independent-review.config.toml` を `$CODEX_HOME/independent-review.config.toml`（既定 `~/.codex/`）へコピーする。read-only sandbox と GitHub への network だけを許可する profile
- `compact-prep`（Claude Code のみ）: `skills/compact-prep/references/setup.md` に従って hook を登録する。Codex ではセッション ID の展開と hook がないため動かない
- `change-design-gate`: 設計成果物の保存先（既定 `work/design-reviews/`）を各 repository の `.gitignore` または `.git/info/exclude` で Git 管理外にする
- `explained-diff-review`: Python 3 と `git` が PATH にあること。`scripts/review_tool.py` がスナップショット取得、レビューデータの検証、画面生成、返信 payload の検証を行う。画面は `assets/review-widget.html` の固定テンプレートから生成し（`--layout page` の単独 HTML はそれを `assets/review-page.html` で包む）、作業ファイル（`snapshot.json`、`review.json`、`widget.html`）は repository の外に置く。Claude Code は `visualize` MCP server、Codex は同梱の `visualize` skill で表示する

## プロジェクト固有の規約との関係

各 Skill は「repository の agent 規約ファイル（`AGENTS.md`、`CLAUDE.md`）が定める規約を優先する」前提で書いている。Issue の運用、worktree の場所、push の既定、契約 ID の体系はプロジェクト側に書き、Skill 本文には持ち込まない。

## 表記

- Skill 本文と commit message は日本語。技術識別子は原文のまま
- `github-issue-flow` と `thermo-nuclear-code-quality-review` の本文は英語（前者は `gh` の出力や GitHub の用語と対応させるため、後者はレビュー文言をそのまま英語コメントに使えるようにするため）
- `explained-diff-review` の本文と参照文書も英語（両ホストの API 名と対応させるため。画面の言語は生成時に `locale` で選ぶ）

## License

MIT
