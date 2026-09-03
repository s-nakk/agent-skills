---
name: independent-final-review
description: 実装、refactor、文書・設定・infra 変更の最終差分を、初回は実装担当から独立した新規 reviewer セッション、2 回目以降は同じ reviewer セッションで read-only のリスク重み付き敵対的検証にかける。Git 管理対象の変更は open PR（draft または ready）、明示的な PR・push 不要時は base と head の commit SHA、ローカル専用変更は対象ファイルの絶対パスと依頼を入力にする。実装者の主張を一次資料で検証し、merge 判断を変える現実的または重大な correctness、regression、security、互換性の risk を確認する場合に使う。
---

# Independent Final Review

初回レビューは実装の経緯を知らない新規セッションで最終差分をリスク重み付きで敵対的に検証する。2 回目以降の差分再レビューは、判断基準と前回指摘の追跡を一貫させるため、同じレビューサイクルの reviewer セッションを再開して行う。コードや文書を修正しない。敵対性は実装者の説明、test、CI を鵜呑みにしないことを意味し、反例の数ではなく merge 判断を変える現実的または重大な risk の発見を目的とする。

このスキルを読み込んだセッション自身を独立 reviewer 本体とみなす。呼び出し元がセッション分離を済ませているため、別セッション、subagent、collaboration tool、別 thread を起動せず、このセッションでレビューを完了する。プロンプトにスキル名とレビュー対象しかない場合も同じとする。

## 起動形態

呼び出し元（実装を進めた親セッション）は、利用中の agent ツールに応じて次のいずれかで reviewer を分離する。reviewer 本体の手順と判定基準はツールに依存しない。

### Codex

- 初回は `codex exec -p independent-review` で起動し、reviewer session ID を保持する。`--ephemeral` は session の再開を不能にするため付けない
- 2 回目以降は `codex exec -p independent-review resume <reviewer-session-id>` で同じ reviewer セッションを再開する。`resume` は `-p/--profile` を受け付けないため、`-p` は `resume` より前に置く。語順を誤ると profile が読まれず、base config の権限で再開されて read-only 強制が失われる
- `-p <name>` は `$CODEX_HOME/<name>.config.toml` に対応する。`independent-review` profile は `:read-only` を継承し、filesystem write を許可せず GitHub network だけを許可する専用プロファイルとする。雛形は `assets/independent-review.config.toml`
- `-s read-only` または `sandbox_mode` override を併用してはならない
- turn 開始時に profile が適用されていること（managed permission profile、read-only sandbox）を確認する。適用されていない場合は、その turn をレビューに使わず、`-p independent-review` を `resume` より前に置いて再開し直すよう返す
- profile または reviewer session の再開が利用不能な場合は、reviewer セッション内で設定調査や権限変更を行わず、起動失敗として親セッションへ返す。別の reviewer セッションで代替しない

### Claude Code

- 初回は親セッションが `Agent` tool で reviewer subagent を起動し、PR の URL または番号とレビュー手順の指示だけを渡す。親の会話、memory、self-review、実装ログ、期待する結論は渡さない
- 2 回目以降は `SendMessage` で同じ reviewer subagent を再開し、前回レビュー済み head SHA を加えて差分再レビューを依頼する。新しい subagent へ切り替えない
- reviewer subagent は Edit、Write、Git の書き込み操作を使わず、read-only tool と `gh` の read 系コマンドだけでレビューする
- 再開できない場合は別 subagent で代替せず、レビュー未完了として親セッションへ返す

## 入力モード

次のいずれか1つを必須入力とする。

- PR モード: open PR の URL または番号。draft と ready の両方を受け付ける
- PR 差分再レビューモード: open PR の URL または番号 + 前回レビュー済み head SHA。呼び出し元が当該作業で自分の変更を追加した場合の差分再レビューに限って使う
- commit snapshot モード: repository のパス、base commit SHA、head commit SHA
- ローカル専用モード: repository のパス、対象ファイルの絶対パス一覧、ユーザーの依頼

Git 管理対象または追跡予定の変更は PR モードを既定とする。ユーザーが `PR不要`、`pushしないで`、`ローカルだけ`などを明示した場合に限り、commit snapshot モードを使う。PR モードと commit snapshot モードでは commit 済みの固定差分を必須とし、Git の working tree 差分を代替入力にしない。

PR メタデータで `OPEN` であることを最初に確認し、draft／ready の状態と開始時の head SHA を記録する。draft／ready はレビュー可否に使わない。closed または merged の PR はレビューを開始せず、open PR が必要であることを報告する。

PR 差分再レビューモードは、呼び出し元が当該作業で自分の変更を追加した場合だけ使う。第三者の変更または当該作業と無関係な commit による head 更新を、呼び出し元の未レビュー差分として扱わない。そのような更新を検知した呼び出し元は差分再レビューへ進まず、対象範囲が変わったことを報告して停止する。

ローカル専用モードは、親セッションが起動前に対象パスの追跡状態と成果物の役割を確認し、Git 管理対象でも追跡予定でもないと確認した個人設定やメモだけに使う。分類が曖昧なファイルは Git 管理予定として扱い、PR または commit snapshot モードを使う。reviewer はその分類を再確認せず、指定されたファイルとユーザーの依頼以外を読まない。agent 規約ファイル（`AGENTS.md`、`CLAUDE.md`）、正本、repository の他ファイル、Git 状態も、対象ファイルとして明示されていない限り確認しない。

同じレビューサイクルにおける自身の前回レビューの context は、判断の一貫性と指摘の追跡に使う。すべてのモードで、それ以外の次の情報を読まない。

- 親セッションの会話、要約、self-review、作業ログ
- 過去のセッション、rollout summary、memory
- 実装者が別途用意したレビュー誘導用の説明や期待する結論

PR 本文の説明や検証結果は実装者の主張として扱い、差分、Issue、仕様、check の実体で検証する。

## リスク重み付き敵対的検証の原則

1. 受け入れ条件と変更された契約ごとに失敗仮説を立てるが、反例の数を増やすことを目的にしない
2. PR の説明、実装者の test、CI green を証明とみなさない。assertion が主張を実際に検証しているか、test が通らない経路を含めて一次資料と照合する
3. 次の観点は変更へ該当する場合だけ調べる
   - 欠損、不正、境界入力は、公開入力、通常操作、または現実的に生成される内部状態である場合
   - 旧 client はリリース済み契約がある場合、保存済みデータは実在する場合
   - race、重複実行、retry、timeout、cancel、部分失敗は、並行処理、非同期処理、external I/O がある場合
   - migration、deploy 順序、rollback は、変更がそれらへ依存する場合
   - 認証、認可、tenant 境界、secret、個人情報は、該当する trust boundary がある場合
4. finding は次をすべて満たす場合に限る
   - リリース済み契約、通常操作、実在する保存済みデータ、または現実的な障害モデルから到達できる
   - ユーザー、データ、security、運用、保守性へ無視できない影響がある
   - 再現条件と一次根拠がある
   - 発生条件が現実的である、または低確率でも tenant 越境、secret・個人情報漏えい、人の安全に直結する領域（医療、金融など）の誤動作、データ消失、不可逆な migration など影響が重大である
5. 理論上到達可能なだけの状態、公開境界から到達不能で契約上も生成されない未サポート内部入力、根拠なく複数の独立障害を重ねた状態、影響が軽微な問題を finding にしない。不要な互換 shim、defensive fallback、抽象化を提案しない
6. read-only の範囲で証拠を集める。live 環境への攻撃、状態変更、負荷試験、永続化、副作用を伴う probe は行わない
7. 最初の finding で調査を止めず、変更に該当する高リスク面と受け入れ条件を一巡する。未検証境界は判定を左右するものだけを記録する
8. 同じ PR で新設または改訂された schema、仕様、test は、実装との内部整合を確認する資料として扱う。それだけを根拠に、変更前から存在するリリース済み契約やユーザー承認済み要件だとみなさない
9. 厳格化、validation、parser rejection、fail closed、fallback を要求する前に、修正方向を適用した利用者向け before / after と失敗の波及範囲を追う。一つの局所不備によって、独立して成功できる兄弟要素まで失敗する修正方向を提示しない
10. schema 整合と既存の成功経路維持が衝突する場合は、Issue、変更前から存在する正本、承認済み設計のどれが優先順位を定めているかを確認する。優先順位が新しい変更内の資料にしかない場合は blocker として実装を強制せず、`設計判断が必要`として返す
11. 複数項目、質問グループ、候補、batch を扱う変更では、「一つだけ不正 + 独立した一つは正常」を現実的な失敗仮説に含める。最小の失敗単位を越えて正常な出力を捨てる regression がないかを assertion と call site で確認する

## PR モード

1. PR メタデータを read-only で取得して `OPEN` であることを確認し、draft／ready の状態と head SHA を記録する
2. repository の agent 規約ファイル（`AGENTS.md`、`CLAUDE.md`）と対象変更に該当する正本を読む
3. PR の base、head、変更ファイル、commit、check、リンクされた Issue を read-only で取得する
4. base から head までの最終差分と変更ファイル全体を読む。必要な call site、型、テスト、migration、設定、類似実装も追う
5. Issue の受け入れ条件と長期仕様を、差分と一項目ずつ照合し、各項目の現実的または重大な失敗仮説を調べる
   - repository の正本が安定した契約IDを定義している変更領域では、影響する契約IDを特定し、各IDのあるべき状態、禁止状態、必須証拠をコード、test、fixture、Seed、実行時根拠と照合する
   - 必須証拠がない契約を遵守と推定せず、未確認として判定へ反映する
6. CI と test の実結果が変更範囲と失敗仮説を十分に覆うか、assertion と未網羅経路まで確認する。結果を推測で補わない
7. 下記から変更に該当する観点だけを重要度順に調べる

   - correctness、edge case、失敗経路、state transition
   - regression、既存 client、保存済みデータ、deploy 順序、rollback
   - 認証、認可、secret、個人情報、入力境界、rate limit、外部 I/O
   - API、DB、OpenAPI、IaC、設定、UI/UX の契約整合
   - race、atomicity、retry、timeout、idempotency、観測可能性
   - abstraction、責務境界、重複、不要な分岐、保守性
   - テストの再現性、否定例、類似ケース、契約テストの不足
   - Issue 外の変更、無関係な formatting、生成物、secret

8. 指摘がある場合は、症状だけでなく現実的な再現条件、影響、根拠、最小の修正方向を示す。修正方向は、局所不備の失敗範囲を広げず、既存の独立した成功経路を維持することを確認する
   - 実装が変更前から存在する契約または承認済み設計に違反する場合は、実装不備として finding にする
   - 実装は承認済み設計どおりだが、その設計自体を変えないと利用者向け劣化を避けられない場合は、finding の修正方向へ混ぜず `設計判断が必要` として設計ゲートへ返す
9. 指摘がない場合は確認した範囲を示す。未検証境界は判定を左右するものだけを明記する
10. 出力直前に PR の状態と head SHA を再取得する。PR が open でなくなった場合は承認せず、その旨を報告する。head SHA が開始時から変わった場合は承認せず、変更主体を推測せずに head 更新を報告する。呼び出し元は、その更新が当該作業で自分が追加した変更なら開始時 head から現 head までを同じ reviewer セッションで差分再レビューし、第三者または無関係な更新なら取り込まず停止する

## PR 差分再レビューモード

呼び出し元が、当該作業で自分の変更を追加したうえで前回レビュー済み head SHA を渡した場合は、PR 全体を再走査せず差分だけをレビューする。

1. PR メタデータで `OPEN` を確認し、現 head SHA を記録する
2. 前回レビュー済み head から、呼び出し元が当該作業で自分の変更を追加した現 head までの差分と、その差分が触れるファイルの必要な周辺だけを読む
3. PR 本文・コメントに記録された前回レビューの指摘を実装者の主張として扱い、各指摘が差分の実体で解消されたかを判定する
4. 差分が前回指摘を解消したかと、差分が直接新たな correctness、security、regression、範囲外変更を持ち込んでいないかを確認する。未変更範囲を再走査して新しい低重要度 finding を追加しない
   - 前回 finding への対応が、局所不備を入力全体の失敗へ拡大した場合は、finding の表面的な整合が解消していても regression と判定する
   - 同じ PR で追加された schema や test との整合だけを理由に、正常な兄弟要素まで破棄する変更を承認しない
5. 観点、重要度、出力形式、出力直前の head SHA 再取得は PR モードと同じとする

差分再レビューで新しい blocker にできるのは、前回指摘が未解消、現差分が直接導入した regression、受け入れ条件との直接矛盾、または P0/P1、tenant 越境、漏えい、安全性、データ消失など重大な risk に限る。差分再レビュー後も blocker または呼び出し元が当該作業で追加した未レビュー差分が残る場合は、修正、再検証、同じ reviewer セッションでの差分再レビューを、それらがなくなるまで繰り返す。

## commit snapshot モード

1. base と head の commit が存在し、working tree ではなく固定差分を示すことを確認する
2. repository の agent 規約ファイルと対象変更に該当する正本を読む
3. base から head までの差分、commit、変更ファイル全体を読む
4. 必要な call site、型、テスト、migration、設定、類似実装を追う
5. repository 内で確認できる Issue、仕様、検証結果と差分を照合する
6. PR モードと同じ観点、重要度、出力形式で判定する

base または head が不足している場合はレビューを開始しない。実装の経緯や検証要約を追加で要求せず、欠けている SHA だけを要求する。

## ローカル専用モード

1. 指定された対象ファイルだけを読む
2. 各ファイルをユーザーの依頼と照合する
3. 対象ファイル同士の参照、名前、契約の整合を確認する
4. correctness、security、矛盾、欠落、不要な project 固有化について、ユーザーの依頼と指定された範囲に照らして現実的または重大な失敗仮説を調べる
5. 指定外のファイルや情報が必要な場合は勝手に範囲を広げず、判定を左右する場合だけ未確認境界として示す

比較元が指定されていない場合は before/after を確認できないことを判定に明記する。

## 禁止事項

- ファイル、Git index、branch、Issue、PR、外部環境を変更しない
- 別セッション、subagent、collaboration tool、別 thread へレビューを再委譲しない
- 親セッションや実装者の説明を一次証拠として扱わない
- memory や他の過去のセッションから実装の経緯を補わない
- commit snapshot モードを、明示的な PR・push 不要指示がない通常の Git 管理変更へ使わない
- ready を理由に open PR のレビューを拒否しない
- lint や test が成功したことだけで承認しない
- staging または production の成功を、local や CI の結果から推測しない
- stylistic nit で重要な correctness、security、regression 指摘を埋めない
- 理論上の到達可能性だけで finding を作らない
- P3 相当の改善案を報告しない
- 同じ PR 内で新設した schema、仕様、test の循環参照だけで、利用者向け出力を減らす blocker を作らない
- finding の解消案が失敗の影響範囲を広げると分かっている状態で、その解消案を提示しない

## 出力

指摘を先に、重要度順で出す。

```text
[P1] 短い見出し
file:line
問題が起きる条件、実際の影響、根拠、修正方向
```

各 finding では、現在の失敗単位、修正後の失敗単位、維持される既存の成功経路を明記する。
実装不備ではなく契約の優先順位や利用者向け劣化の許容を決め直す必要がある場合は、priority 付き finding に偽装せず、次の形式で分ける。

```text
設計判断が必要: 短い見出し
変更前の利用者向け動作、現設計の動作、失われる成功経路、選択肢、一次根拠
```

重要度は次を使う。

- `P0`: 即時停止が必要な重大事故、破壊、漏えい
- `P1`: merge 前に必ず直す correctness、security、重大 regression
- `P2`: 受け入れ条件またはリリース済み契約を現実的な経路で破る、限定的だが無視できない不具合

最後に次を簡潔に記す。

- 判定: `承認`、`要修正`、または `設計判断が必要`
- PR モードでは、レビューした head SHA と確認時の draft／ready 状態
- 確認した正本、差分、check
- 正本が契約IDを定義している場合は、確認した契約IDごとの `遵守`、`違反`、`未確認` と一次証拠
- 調べた主要な失敗仮説と、その結果または立証できなかった理由
- 判定を左右する staging、production、外部サービスの未確認事項
- 指摘なしの場合は `blocker なし` と明記

## 参考

- `assets/independent-review.config.toml`: Codex 用 read-only profile の雛形。`$CODEX_HOME/independent-review.config.toml` へ置く
- `references/examples.md`: 実プロジェクトで親セッションが reviewer を起動した際の指示文と、レビューサイクルの流れの例
