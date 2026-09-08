# プロジェクト補助規約 — workflow

プロジェクトの `AGENTS.md` の一部。運用選択は同じディレクトリの `settings.md`、source・仕様・test の相対パスは作業対象のプロジェクトルートを基準にする。共通の品質基準は GLOBAL を参照する。PR 本文への記録は PR を作る場合だけに適用し、作らない場合は選択済みの変更記録と完了報告へ残す。staging・production の確認は該当環境へ反映する場合だけに適用する。

## 標準フロー

### 調査とスコープ確定

設計承認に関する手順は `settings.md` で承認対象にした変更だけに適用する。Issue を使わない場合は以下の Issue 必須条件を適用しない。

- 最初に直近の依頼、現行差分、関連 Issue（採用時）、実コード、実環境を確認する
- production、staging、認証、CI、監視の問題は、推測修正より先に実ログ、read-only の実 API probe、実データ、実 service state で failing path を特定する
- 設計承認を採用する変更では、採用済みの設計承認手順を使う。Issue を使う変更は既存 Issue を read-only で採用するか、scope と受け入れ条件を含む Issue を一回だけ起票する。Issue を使わない変更は名前で識別する。その変更の一時設計ディレクトリへ、選択された形式の設計、受け入れ条件、テストケース、版管理の記録を作成して提示する
- 最初の依頼に `実装して` や `最後まで進めて` が含まれていても設計承認とは扱わない。選択形式の設計提示後に対象版への明示的な OK を得るまで、起票済みまたは採用済み Issue の変更、Worktree 作成、実装、test 作成、tracked file の編集、commit、push、PR 作成へ進まない。承認後に Worktree、SDD/TDD へ進み、実装中に承認済み設計から外れる必要が生じた場合は停止し、同じ変更の一時設計ディレクトリへ次版の設計資料を追加して再承認を得る
- ユーザーが複数の作業を依頼した場合は、安全性や業務判断で止まる必要がない限り、全項目を完了してから報告する

### 実装前の設計承認ゲート

この節は承認対象の変更だけに適用する。HTML・SVG・台帳の具体的な形式指定は HTML を選んだ場合だけに適用し、別形式では同じ判断材料をその形式で提示する。

- 設計承認の対象は `settings.md` に確定した変更条件に従う。全変更を選んだ場合はバグ修正、hotfix、新機能、refactor、UI、API、DB、認証、認可、設定、infra、CI/CD、依存関係、長期仕様、tracked document の変更を規模にかかわらず含める
- 設計成果物は Git 管理外の `settings.md` で定めた保存先に置く。変更名、現在版、全体状態、版履歴を記録する。Issue を使う場合だけ番号と URL も表示する。現状と変更後、処理パイプライン、影響範囲を図解し、改訂は上書きせず版を増やす。HTML を選択した場合は `index.json` と `design-v<N>.html` を使う
- 処理パイプラインは Mermaid source を HTML 内へ残し、事前に inline SVG へ render するか、同等の情報量を持つ inline SVG / HTML で表示する。実在する component、各段階へ渡る主要データ、判断条件、正常経路、失敗・縮退経路を記載し、`処理1`、`判定`、`結果`のような抽象名だけで済ませない。外部 CDN や表示時 network access には依存しない
- 設計 HTML には、判断サマリー、一次根拠、現状と原因、変更後の仕様、変更点、scope と非 scope、安全性・互換性・移行、番号付き受け入れ条件、対応する番号付きテストケース、承認後の実装計画、判断事項、承認欄を含める。さらに正常系、境界・否定例、失敗・縮退の最低3件について、現実的な入力値、前提、通過するパイプライン、期待出力、対応AC / TCを示す具体例を含める
- 承認は 選択形式の設計提示後に対象版を明確に指す返答だけを有効とする。過去の承認、別テーマへの承認、設計提示前の実装依頼を流用しない。設計承認は production 変更、deploy、DB write、merge、ready 化、auto-merge、設計外の scope 拡大を許可しない
- 説明、状態確認、read-only 調査、review-only だけを求められ、変更へ進まない依頼はこのゲートの対象外とする。調査中に修正が必要と判明した場合は、編集へ移る前にゲートへ切り替える
- 一時設計ディレクトリは PR の merge またはユーザーによる作業の明示的な破棄まで保持する。merge 時は承認版の scope、受け入れ条件、テストケースが PR と、その変更に該当する長期仕様、実装、test または検証証拠へ引き継がれたことを確認してから削除する。該当しない成果物は理由を確認し、存在を要求しない。破棄時は残存する tracked 変更、Worktree、open PR がないことを確認してから削除する。どちらも対象変更のディレクトリだけを完全パスで特定し、削除したことを報告する

### Issue

この節は Issue を使うと決めた変更だけに適用する。Issue なしの場合、起票・番号・Refs・Project status・Issue 連携を要求しない。

- Issue の起票時本文は個別変更の管理単位、初期 scope、初期受け入れ条件の不変な snapshot とする。設計レビューで確定または改訂された詳細 scope、仕様、受け入れ条件、テストケースは承認版設計資料を実装開始時の正本とし、実装開始後は PR、長期仕様、source code、test へ引き継ぐ。起票後の進捗、原因、修正内容、検証結果は PR 本文と完了報告へ記録する
- **既存 Issue は読み取り専用とする。** Issue 番号または URL が返って起票が完了した時点から、Codex は本文、タイトル、comment、label、assignee、milestone、open / closed、pin、lock、transfer、Project item と Project field を変更しない
- 例外は、ユーザーが現在の会話で、対象 Issue と変更する field または操作を具体的に明示した場合だけとする。`Issue に対応して`、`調査して`、`実装して`、`進めて`、`完了して`、`PR を作って`、`起票してから対応して` は既存 Issue 更新の許可ではない
- Issue 作成の許可は一回の create 操作だけを許可する。作成結果が返った後に、不足、誤記、調査結果、受け入れ条件、進捗を追記するための edit を行わない。修正が必要なら、既存 Issue を変更せずユーザーへ対象 field と変更案を示して明示指示を待つ
- 上の gate は CLI、REST API、GraphQL、GitHub connector、browser、automation のすべてに適用する。`gh issue edit`、`gh issue close`、`gh issue reopen`、既存 Issue への `gh api` の `PATCH` / `DELETE`、`updateIssue`、label / assignee / Project 更新 mutation、Issue comment 作成を別経路で迂回しない
- Issue を変更する GitHub 操作の直前に、現在のユーザー依頼から `対象 Issue`、`対象 field / 操作`、`変更後の値または目的` の三つを引用できるか確認する。一つでも欠ける場合は mutation を実行せず read-only を保つ
- `Refs #番号` を既定とする。`Fixes`、`Closes`、`Resolves` は PR merge により既存 Issue を更新するため、ユーザーが現在の会話で対象 Issue の自動 close を明示した場合だけ使う
- ユーザーが復元を明示した場合は、編集履歴から対象 field の直前状態を特定し、指定された field だけを戻す。復元後は Issue state と Project status を別々に確認する
- 以下の close 条件と Project status 条件は、ユーザーが変更を明示した場合または外部 automation の結果を確認するための制約であり、Codex に変更権限を与えない
- Issue が長期維持する機能契約または上位要件を変える場合は、同じ PR で `settings.md` に記録した長期仕様・上位要件の正本を同期する
- プルリクエスト（PR）本文には `Refs #番号` を書く
- 個別変更の管理には GitHub Issue を使い、ローカルのタスク一覧やロックファイルは作成・更新しない
- 実環境へ反映する変更は、対象となる staging と production の確認が終わる前に Issue を close しない
- deploy 対象がない文書、設計、調査の Issue も自動で close せず、ユーザーが明示した場合だけ close する
- Issue 対応の説明は、非エンジニアにも分かる日本語を先に置く。技術識別子が必要な場合は `日本語（識別子）` の順で補足する
- 進捗、原因、修正内容、検証結果は PR 本文と完了報告に書き、Issue comment へ重複させない

### Worktree と Git

Git がある変更だけに適用する。専用 Worktree の必須条件は `settings.md` で Worktree を選んだ場合だけに適用する。checkout を選んだ場合は作成・移動・撤去を要求しない。

- 編集前に `git ls-files` と `git check-ignore` で、追跡対象、追跡予定、個人ローカルの境界を確認する
- Worktree の作成先は `settings.md` で確定した場所を実行環境で解決する。名前には Issue 番号または変更内容を識別できる短い名前を使う
- Git 追跡対象または追跡予定の project file は、当該作業専用の clean な Worktree 内でだけ編集する
- Worktree 用の branch は `settings.md` と現物から確認した base を使う。remote がある場合はその remote を fetch して対象 base を確認し、remote がなければ fetch を要求せず、確認したローカル base から作る。`origin` や `main` の存在を仮定しない
- 既存 PR を修正する場合は、その PR の head branch を選択した作業場所で使う
- main checkout と unrelated な未 commit 差分を変更に混ぜない
- `git stash` と `git stash pop` は使わない
- Worktree の撤去前に、自分の background process の終了、選択した完了地点と必要なレビューの完了、成果物の保存先を確認する。push 済みの確認は push を選んだ変更だけに適用する
- `git worktree remove <path>` は `--force` なしを既定とする。未 commit の変更や、まだ必要な未公開成果物があれば Worktree を保持して場所と残件を報告する。撤去のために commit・push・PR を追加しない。選択した保存先で成果物が保持され、clean でローカル作業が残らず、撤去が許可された範囲なら削除する

### SDD と TDD

- 新機能と大幅変更は、`settings.md` に記録した仕様・開発フローの正本 に従い、受け入れ条件を含む仕様成果物を実装前に更新する
- バグ修正は、修正コードより先にバグを再現するテストを書き、期待する理由で Red になることを確認する
- Green になる最小の実装を行い、Green を維持したまま refactor する
- 振る舞いを変えない refactor は、変更前に関連テストが Green であることを確認し、移動と仕様変更を同じ工程へ混ぜない
- 文言、色、純粋な layout だけの変更は SDD と Red の対象外とする。UI の振る舞いまたは UX contract が変わる場合は回帰テストを追加する
- 振る舞いと環境契約を変えない設定整理は Red の対象外とし、既存 check と差分確認で非変更を検証する
- hotfix で先行テストを作れない場合は、理由、影響範囲、事後補完の記録先と期限（Issue 採用時は Issue）を残す
- test 対象外の変更は、作業種別表に定めた差分確認と関連 check を完了条件とする

### 検証、commit、push、draft PR

- 変更範囲に対応する lint、type-check、test、build、format、migration、Terraform、contract check を実行する
- 検証が通ったら `settings.md` の Git 完了地点まで進める。commit を選んだ場合だけ変更範囲を日本語の commit message で固定する。push・draft PR も選択した場合だけ続ける
- レビュー入力は `settings.md` の方式に従う。PR を作らず commit を許可する変更は base と head の commit snapshot、commit しない変更は固定された変更前後ファイルと差分を使う。選択した入力を扱える独立 reviewer を確認し、レビューのために Git の完了地点を勝手に引き上げない
- secret、範囲外差分、破壊的操作、大規模 refactor、失敗した検証がある場合は自動 publish を止めて理由を報告する
- 同じ branch の draft PR があり、auto-merge が無効なら、その PR を更新する
- 既存 PR が ready または auto-merge 有効なら、自動更新せずユーザーへ確認する
- PR は既定で draft とし、タイトルに `[Codex]` など AI や agent 由来の prefix を付けない
- ready 化、merge、auto-merge は、その会話でユーザーが明示した場合だけ行う。CI green や過去の許可を merge 権限とみなさない
- draft PR 作成時の本文には、対象範囲、受け入れ条件、検証結果、独立レビュー待ちであること、staging と production の未確認事項を書く。独立レビュー完了後に review 結果を追記する
