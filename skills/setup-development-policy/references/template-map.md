# 配布原本と展開先

配布版: 2。元端末の GLOBAL と基準プロジェクトの AGENTS.md・補助規約から抽出する。新しい共通開発方針を一から生成するための雛形ではない。

`<Codex設定先>` は `CODEX_HOME` が設定されていればその実値、未設定ならユーザーホームの `.codex`。Windows と macOS のホームは導入先で解決する。`<Project>` はユーザーが対象にしたプロジェクト。

| 元の役割 | 配布原本 | 展開先 |
|---|---|---|
| GLOBAL の応答・調査・品質・サブエージェント方針 | `assets/global/AGENTS.md` | `<Codex設定先>/AGENTS.md` |
| GLOBAL の言語・互換性規約 | `assets/global/rule-reference/coding.md` | `<Codex設定先>/rule-reference/coding.md` |
| Project の入口・作業別検証・固有の追加条件 | `assets/project/AGENTS.md` | `<Project>/AGENTS.md` |
| Project の設計・Issue・Git・SDD/TDD 手順 | `assets/project/rule-reference/workflow.md` | `<Project>/.codex/rule-reference/workflow.md` |
| Project の独立レビュー・差分再レビュー | `assets/project/rule-reference/review.md` | `<Project>/.codex/rule-reference/review.md` |
| 導入先ごとの運用選択・実在する正本 | `assets/project/rule-reference/settings.md` | `<Project>/.codex/rule-reference/settings.md` |

表の配布原本パスは Skill ルート基準。`AGENTS.override.md` が優先される場合は有効な入口を更新し、読まれない通常ファイルだけを変更して完了にしない。

## 除外・置換したもの

- プロダクト名、クリニック・患者チャットの業務契約、LLM 呼び出し回数、検索候補や回答の契約ID、医療向けレビューの具体的な観点: 配布しない。業務専用の `domain.md` 自体を展開しない
- 元端末のユーザー名・ホーム・プロジェクトの絶対パス: 展開先から解決する参照へ置き換える
- 特定の技術スタック・バージョン、公開済みという宣言、CI の時刻・job 名・hook・build コマンド、固定の仕様パス: 導入先で確認し `settings.md` に記録する
- Issue 必須、全変更の HTML 承認、Worktree 必須、draft PR 完了、レビュー対象、Git への保存方針: 固定の全プロジェクト規則にせず、元の手順へ運用選択の適用条件を加える
- 個人用 reviewer profile の起動コマンド: 導入先で利用できる方式を確認して保存する。独立性・固定対象・同じ担当の差分再レビュー・リスクに基づく判定は維持する
- Project 側に再掲されていた共通の read-only、warning/error、破壊的操作、process の終了、サブエージェントの一般条件: GLOBAL を参照する。Project に残すのは、そのプロジェクトの具体的な手順と追加条件
- 基準プロジェクトにあった本番変更・外部副作用の明示確認、probe の無副作用確認、影響・backup・rollback の提示: 業務に依存しないため GLOBAL へ一度だけ移す

## 更新と既存の v1

Skill 自体の更新で既存プロジェクトを自動変更しない。導入・更新の依頼時に原本・既存本文・保存済みの選択を比較し、独自条件を保持する。参照先だけ変える場合も、その参照が有効になることを確認する。

v1 の `.agent-policy/core.md`・`project.md` がある場合は、共通方針は GLOBAL、回答と固有条件は Project へ移す差分を作る。元の設定を再質問しない。新しい入口と参照が有効で、移した内容に抜けがなく、他に参照元がないと確認してから、明示された移行範囲の旧ファイルだけを撤去する。移行の指示がなければ削除せず、二重適用を避ける案を示す。
