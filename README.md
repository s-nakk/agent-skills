# agent-skills

Claude Code と Codex の両方で使う、開発フロー用の自作 Skill 集（`compact-prep` だけは Claude Code 専用）。
プロジェクト固有の情報は本文から外し、実例だけを各 Skill の `references/examples.md` に匿名化して残している。

## Skill 一覧

| Skill | 役割 | 主な依存 |
|---|---|---|
| [`independent-final-review`](skills/independent-final-review/SKILL.md) | 実装者から独立した reviewer セッションで、PR や commit 差分を read-only のリスク重み付き敵対的検証にかける。再レビューは同じ reviewer を再開する | Codex: `assets/independent-review.config.toml` の profile。Claude Code: subagent |
| [`change-design-gate`](skills/change-design-gate/SKILL.md) | 変更に着手する前に、処理パイプライン図・具体例・受け入れ条件・テストケースを含む自己完結 HTML を作り、明示承認まで実装を止める | `gh`、`assets/` の HTML と台帳の雛形 |
| [`github-issue-flow`](skills/github-issue-flow/SKILL.md) | GitHub Issue を起点に、既存 Issue を変更せず worktree 分離・SDD/TDD・検証・draft PR・独立レビューまで進める定型フロー | `gh` |
| [`thermo-nuclear-code-quality-review`](skills/thermo-nuclear-code-quality-review/SKILL.md) | 抽象化の質、巨大ファイル化、条件分岐の増殖を極めて厳しく審査する保守性レビュー | なし |
| [`compact-prep`](skills/compact-prep/SKILL.md) | コンテキスト圧縮の前に、採用・却下した判断と次の一手を状態ファイルへ退避する。**Claude Code 専用** | `assets/compact-state-hook.py` を hook 登録（`references/setup.md`） |

想定する組み合わせ: `github-issue-flow` で Issue を確定 → `change-design-gate` で設計承認 → 実装 → draft PR → `independent-final-review`。`thermo-nuclear-code-quality-review` は保守性を別軸で見たい時に追加で使う。

## 導入

### skills CLI（推奨）

```bash
npx skills add s-nakk/agent-skills
```

### clone + symlink

Codex は `~/.agents/skills` を、Claude Code は `~/.claude/skills` を読む。`scripts/install.sh` は両方へ symlink を張るので、`git pull` 1 回で両ツールに反映される。

```bash
git clone https://github.com/s-nakk/agent-skills.git ~/projects/agent-skills
~/projects/agent-skills/scripts/install.sh
```

`scripts/install.sh` は `skills/*` を `~/.agents/skills/<name>` と `~/.claude/skills/<name>` へ symlink する。対象は `AGENT_SKILLS_DIRS`（`:` 区切り）で変えられる。既存の実体ディレクトリがある場合はそれを飛ばして報告し、最後に exit 1 を返す。

### Skill ごとの追加設定

- `independent-final-review`（Codex）: `skills/independent-final-review/assets/independent-review.config.toml` を `$CODEX_HOME/independent-review.config.toml`（既定 `~/.codex/`）へコピーする。read-only sandbox と GitHub への network だけを許可する profile
- `compact-prep`（Claude Code のみ）: `skills/compact-prep/references/setup.md` に従って hook を登録する。Codex ではセッション ID の展開と hook がないため動かない
- `change-design-gate`: 設計成果物の保存先（既定 `work/design-reviews/`）を各 repository の `.gitignore` または `.git/info/exclude` で Git 管理外にする

## プロジェクト固有の規約との関係

各 Skill は「repository の agent 規約ファイル（`AGENTS.md`、`CLAUDE.md`）が定める規約を優先する」前提で書いている。Issue の運用、worktree の場所、push の既定、契約 ID の体系はプロジェクト側に書き、Skill 本文には持ち込まない。

## 表記

- Skill 本文と commit message は日本語。技術識別子は原文のまま
- `github-issue-flow` と `thermo-nuclear-code-quality-review` の本文は英語（前者は `gh` の出力や GitHub の用語と対応させるため、後者はレビュー文言をそのまま英語コメントに使えるようにするため）

## License

MIT
