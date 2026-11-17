# 実例（匿名化済み）

医療系 SaaS の repository で運用している形。プロジェクト名、Issue 番号、契約 ID は置き換えてある。

## 親セッションが Codex で reviewer を起動する

初回。PR 番号とスキル名だけを渡す。

```bash
~/.agents/skills/independent-final-review/assets/run-codex-review.sh \
  'Use $independent-final-review to review PR #1234 of this repository. Do not read memory or prior sessions.'
```

モデルや reasoning effort を指定する場合は prompt の前に置く（例: `-m <model> -c model_reasoning_effort=high`）。出力に含まれる session ID を控える。差分再レビューは同じラッパーに `resume` を渡す。ラッパーが `-p` を `resume` より前に置く。**`resume` は初回の `-m` / `-c` を引き継がず、`config.toml` の既定値で再開する**ので、初回と同じ `-m` と `-c model_reasoning_effort=...` を `resume` の前に毎回付け、出力ヘッダーの `model:` と `reasoning effort:` で確かめる。

```bash
~/.agents/skills/independent-final-review/assets/run-codex-review.sh -m <model> -c model_reasoning_effort=high resume <reviewer-session-id> \
  'Re-review PR #1234 with $independent-final-review. Previously reviewed head: a1b2c3d. Review only the diff from that head to the current head.'
```

prompt では PR を URL ではなく番号で渡す。worktree 分離のガードを持つ repository では、コマンド行の GitHub URL や `$skill` 参照を含む引数が検証できないとして起動が止まることがある。止まった場合は、起動行をスクラッチの shell スクリプトに書き、`bash <script> > <log>` で実行する。レビューは長時間かかるので、出力をファイルへリダイレクトしてバックグラウンドで実行する。

## 親セッションが Claude Code で reviewer を起動する

`Agent` tool の prompt に渡す文面。親の判断や実装ログを含めない。

```text
あなたは独立 reviewer です。独立レビュースキル（independent-final-review）の手順に従い、
PR https://github.com/<owner>/<repo>/pull/1234 を PR モードで read-only レビューしてください。
memory、過去セッション、この指示以外の文脈は参照しないでください。
ファイル編集と Git 書き込みは禁止です。
```

再レビューは同じ subagent へ `SendMessage` で送る。

```text
同じ PR の差分再レビューです。前回レビュー済み head は a1b2c3d です。
その head から現 head までの差分だけを対象にしてください。
```

## レビューサイクルの流れ

1. draft PR 作成 → 初回レビュー（PR 全体）
2. blocker があれば親が修正。ただし承認済み設計から外れる修正（追加ガード、fallback、責務移動、契約を新設する test など）は `設計差分` として止め、ユーザーへ判断を返す
3. 契約内の修正は commit、push → 同じ reviewer で差分再レビュー
4. blocker と未レビュー head がなくなるまで 2〜3 を繰り返す
5. PR 本文に、レビュー済み head SHA、指摘と対応、承認済み設計版、レビュー起因の設計差分の有無を記録する

## 契約 ID を持つ repository での判定例

repository の長期仕様が `PIPE-01`〜`PIPE-11` のような安定した契約 ID を定義している場合、reviewer は影響する ID ごとに次を並べる。

```text
PIPE-04 遵守: 決定的テスト WidgetChatRouteTests.RouteFallsBackToFaq が禁止状態を assertion
PIPE-07 未確認: fixture に否定例がなく、実行時マスタの採用根拠が差分から読めない
```

`未確認` を `遵守` に丸めない。
