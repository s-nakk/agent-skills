---
name: compact-prep
description: >-
  コンテキスト圧縮（/compact・auto compact）の前にセッション状態を状態ファイルへ保存するスキル。
  採用・却下した設計判断とその理由、進行中タスク、制約、編集中ファイル、圧縮後の自分への申し送りを
  固定フォーマットで記録し、圧縮後の文脈喪失（却下案の再提案、検証前デプロイ、作業ログと作業指示の混同）を防ぐ。
  ユーザーが /compact を実行しようとしている時、コンテキスト使用率の警告（context-usage-warning）が
  注入された時、「圧縮の準備をして」「状態を保存して」と言われた時に必ず使う。
  Claude Code 専用（セッション ID の展開と hook 連携が Claude Code の仕組みに依存する）。
argument-hint: ""
allowed-tools:
  - Read
  - Write
  - Bash
---

# compact-prep — コンテキスト圧縮前のセッション状態保存

## 目的

`/compact` や auto compact は会話履歴を要約に置き換える。要約は「過去の作業ログ」としては妥当でも、
「意思決定の構造」（どの案を採用し、どの案をなぜ却下したか）と「次に何をすべきか」が脱落しやすい。
このスキルは圧縮前にそれらを固定フォーマットの状態ファイルへ退避し、圧縮後のセッションが
却下済みの案を再提案したり、検証前の変更を検証済みと思い込んだりすることを防ぐ。

## 前提

- **Claude Code 専用。** セッション ID の展開（`${CLAUDE_SESSION_ID}`）と圧縮後の hook 連携が Claude Code の仕組みに依存するため、Codex など他ツールでは Step 1 のハードゲートで中止する。他ツールで同等の運用をする場合は、そのツールのセッション ID 取得手段と hook 相当を別途定義する
- 状態ファイルの保存先は `COMPACT_STATE_DIR` 環境変数、未設定なら `~/.claude/compact-state`
- 圧縮後の自動読み込みは `assets/compact-state-hook.py` を hook として登録することで動く。登録手順は `references/setup.md`
- セッション ID は実行環境が提供する変数から取る。Claude Code では `${CLAUDE_SESSION_ID}`

## 手順（厳守）

### Step 1: セッション ID の確認（ハードゲート）

このセッションのセッション ID は `${CLAUDE_SESSION_ID}` である。

- 上記が空文字列や未展開のプレースホルダーのままの場合、**状態ファイルを作成せず中止**し、
  「セッション ID が取得できないため compact-prep を実行できません」とユーザーへ報告する。
  推測したファイル名で書いてはならない

### Step 2: 保存先の準備と古いファイルの掃除

```bash
STATE_DIR="${COMPACT_STATE_DIR:-$HOME/.claude/compact-state}"
mkdir -p "$STATE_DIR"
find "$STATE_DIR" -type f -mtime +7 -delete
```

### Step 3: 状態ファイルの作成

`$STATE_DIR/${CLAUDE_SESSION_ID}.md` へ、**以下の見出しをすべて・この順序で**含む
Markdown を Write する。該当がないセクションは見出しごと削除するのではなく `(none)` と書く
（見出しの欠落 = 記入漏れとして検出できるようにするため）。

```markdown
# Session State (compact-prep)

- Saved At: <ISO 8601 のローカル時刻>
- Working Directory: <現在の作業ディレクトリ>
- Branch: <現在の git ブランチ。リポジトリ外なら (none)>

## Active Plan

<計画ファイルや仕様書のパスと、その中で現在どこにいるか。なければ (none)>

## Current Phase

<今どの段階か。例: 「再現テスト作成済み・Red 確認済み、最小実装の途中」>

## Task List

<進行中・未着手のタスクの要約。タスク管理ツール使用中ならその ID も>

## Session Decisions

<このセッションで確定した意思決定。最重要セクション。形式:>
- 採用: <採用した方針> — 理由: <理由>
- 却下: <却下した方針> — 理由: <却下した理由>

## Constraints / Blockers

<このセッションで判明した制約・ブロッカー・ユーザーからの明示指示（例: push 禁止、〇〇は変更不可）>

## Parallel Work

<進行中の subagent・バックグラウンドタスク・別セッションとの分担があれば。なければ (none)>

## Editing Files

<未コミット・未検証の変更があるファイルと、その検証状態。「テスト未実行」「lint 未確認」等を明記>

## Recovery Notes

<圧縮後の自分への申し送り。「次にやること」を具体的な 1 手目から書く。
 例: 「tests/Foo.test.ts:120 のテストが Red のまま。原因は △△ と特定済みで、次は □□ を修正する」>
```

記入時のルール:

- 会話で実際に確定した事実だけを書く。推測・願望を書かない
- 却下案には必ず却下理由を付ける（理由のない却下は圧縮後に再提案される）
- 固有名詞・ファイルパス・行番号・Issue/PR 番号は省略せず具体的に書く

### Step 4: 記入漏れの検証

書き込んだファイルに対して固定見出しがすべて存在することを確認する:

```bash
STATE_DIR="${COMPACT_STATE_DIR:-$HOME/.claude/compact-state}"
f="$STATE_DIR/${CLAUDE_SESSION_ID}.md"
for h in "## Active Plan" "## Current Phase" "## Task List" "## Session Decisions" "## Constraints / Blockers" "## Parallel Work" "## Editing Files" "## Recovery Notes"; do
  grep -qF "$h" "$f" || echo "MISSING: $h"
done
```

`MISSING:` が 1 件でも出たら Step 3 に戻って追記する。

### Step 5: 完了報告

ユーザーへ次を報告して終了する:

1. 状態ファイルの保存先パス
2. 「準備ができたので `/compact` を実行してください」という案内

**このスキルは `/compact` 自体を実行しない**（compact はユーザーが打つスラッシュコマンド）。
圧縮後は SessionStart(compact) hook が状態ファイルの読み込み指示を自動注入する。
