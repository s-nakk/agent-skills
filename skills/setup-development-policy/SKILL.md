---
name: setup-development-policy
description: Codex の GLOBAL と Project に、既存の開発ルールから固有情報を除いた AGENTS.md・補助規約を展開・更新する。Issue など未確定の運用だけ対話で決め、共通方針は GLOBAL、プロジェクトの手順と選択は Project に分ける。Windows と Mac の別端末への導入にも使う。通常の実装依頼では再セットアップしない。
---

# GLOBAL と Project の開発ルールを展開する

配布原本は、元端末の GLOBAL と基準プロジェクトの AGENTS.md・補助規約から、固有名・端末パス・業務契約・実環境の固定値を除いたもの。原本の内容と役割を保って展開し、短い別の共通規約へ書き換えたり、共通本文を GLOBAL と Project の両方へコピーしたりしない。

この Skill は Codex 向けの規約を展開する。別ツール用の `CLAUDE.md` は勝手に同期しない。

## 対象と既存状態を確認する

[原本と展開先の対応](references/template-map.md) を読み、対象の GLOBAL 設定ディレクトリとプロジェクトを特定する。Skill の配置先を対象プロジェクトにしない。GLOBAL + Project を標準の導入案とするが、依頼や保存済み範囲に GLOBAL が含まれていなければ、その変更範囲だけを確認する。GLOBAL のみ・Project のみという明示指定は守る。

編集前に、対象範囲で次を read-only で確認する。

- 既存の GLOBAL・Project・上位・子ディレクトリの規約、`AGENTS.override.md`、既存の参照先と運用選択
- 実際の OS・シェル・ツール・`CODEX_HOME`。Windows ネイティブと WSL を区別する。端末間の導入は [OS とパスの扱い](references/platforms.md) を読む
- Project を対象にする場合は manifest・lockfile・仕様の入口・CI・Git の有無・現行差分・追跡と ignore の状態。バージョン、コマンド、リリース状態は現物から取得する

元端末の GLOBAL や基準プロジェクトへのアクセスは必要ない。導入元は同梱原本、導入先の事実は導入先から読む。secret は読出・出力・共有しない。既存の設計承認・作業場所など今回にも適用される条件は守るが、未導入の原本から今回の追加承認や Issue 必須を推定しない。

## 運用が分かれる項目だけ決める

Project の導入時は [運用選択](references/setup-options.md) を参照する。既存規約で確定・会話で指定済み・未確定・非該当を分け、未確定の項目だけ対話ツールの上限に合わせて少数ずつ質問する。ツールがなければ通常の会話を使う。既存運用に近い案を最初に示し、違いを短く伝える。

Issue、設計承認、Git 完了地点、作業場所、レビュー、保存範囲は独立した選択。Issue なしでも設計やレビューは可能であり、架空の Issue 番号を要求しない。GLOBAL だけの導入で Project の運用を質問しない。返答・推薦の初期選択・時間経過を承認とみなさない。

再実行では保存済みの選択を維持し、変更依頼か環境変化で実行不能な項目だけ見直す。

## 原本を役割ごとに展開する

- GLOBAL: `assets/global/AGENTS.md` と `assets/global/rule-reference/coding.md` を実際の Codex 設定先へ展開する。プロジェクト名、Issue 運用、Project のファイルへの参照を入れない。GLOBAL の配下参照は設定ディレクトリ基準にする
- Project: `assets/project/AGENTS.md` と `assets/project/rule-reference/` を、Project の入口と `.codex/rule-reference/` へ展開する。`settings.md` の記入説明を確定した選択と現物の情報に置き換える。GLOBAL の本文をコピーしない
- 原本の workflow・review は手順の原型として保持し、選んだ運用の適用条件を `settings.md` で確定する。不要な業務ルール・不存在の仕様・未導入の Skill や reviewer profile を補わない
- Project のみを依頼された場合は、有効な GLOBAL と coding 規約が参照可能で、必要な共通条件を満たすことを確認する。不足時は不足内容と GLOBAL 追加案を示し、その回答を待つ。Project 側へ共通本文を複製して埋めない

既存の同等ファイルがあればその役割へ統合し、別名の同じ規約を増やさない。`AGENTS.override.md` が有効なら、既存本文を保って有効な入口へ反映する。共通規約の変更と、GLOBAL に対する Project の明示的な例外を区別する。削除・優先順位変更・未選択の操作が必要なら、具体的な差分と影響を示して確定してから反映する。

変更候補の全ファイルを対象外の一時ディレクトリへ退避し、既存本文・独自変更を保って差分だけ適用する。GLOBAL を今回展開する場合は、その入口と coding への参照を先に確認してから、Project の参照を切り替える。途中で失敗した場合は適用済みと未適用を分け、欠けた参照を残して完了にしない。保存済みの内容と同じなら書き直さない。

Project の追跡・ローカル保存は選択と既存状態に従う。追跡する入口の依存ファイルも共有し、ローカル保存と衝突する追跡済みファイルを勝手に untrack しない。exclude の場所は `git rev-parse --git-path info/exclude` で取得する。Worktree からも規約へ到達できる配置を確認し、ローカル規約が無い別 checkout で読めると推定しない。必要なコピーまたは参照の解決方法を `settings.md` に記録する。

## 検証と更新

- GLOBAL の入口から coding、Project の入口から settings・workflow・review へ、実際の配置で到達できる。override と Worktree も対象に含まれる場合は確認する
- GLOBAL に Project の参照・固有条件がなく、Project に GLOBAL の共通本文が再掲されていない。Project の手順に必要な参照と明示的な追加・例外は重複とみなさない
- 原本の各役割が展開済みで、配布版、適用範囲、選択の根拠を保存した。Project は settings に記録し、GLOBAL のみなら入口へ配布版と適用範囲だけを記す。未記入の雛形、元端末のパス、架空の仕様や能力が残っていない
- Issue なし・承認対象外・ローカル完了の選択を、workflow・review や他 Skill の既定で覆していない
- 日本語・空白を含むパス、OS 別のコマンドと確認状況を区別した。規約導入を理由に製品全体の test・本番操作・有料 API を実行していない

v1 の `.agent-policy/` がある場合は、[移行手順](references/template-map.md) に従って役割ごとに引き継ぐ。元の独自条件・選択を捨てない。

今回の規約変更に必要なレビュー・公開は、導入前の規約と現在の依頼に従う。将来の Git 完了地点を保存したことだけを今回の commit・push・PR 権限とみなさない。検証・レビュー後、GLOBAL と Project それぞれの変更先、選択した運用、重複と参照の確認、残件を短く報告する。未確認の OS 動作や消費削減を成功扱いにしない。
