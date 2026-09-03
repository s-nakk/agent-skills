# 実例（匿名化済み）

医療系 SaaS の repository で運用している形。Issue 番号と機能名は置き換えてある。

## 依頼と最初の応答

依頼: 「Widget で予約方法を尋ねても予約リンクが出ないことがある。直して PR まで作って」

応答の要点:

1. 「PR まで」は承認ではないと明示し、まず一次資料（会話ログ、route 選択の実装、fixture、長期仕様の契約 ID）を読む
2. Issue が指定されていないので、初期 scope / 非 scope / 初期 AC を含む Issue を 1 回だけ起票（例: #1200）
3. `work/design-reviews/issue-1200/index.json` と `design-v1.html` を作る
4. HTML をプレビューで開き、「Issue #1200 と紐づけて設計 HTML を作成しました。……承認を明示してください」で停止

## index.json の遷移

```json
{ "current_version": "design-v1", "status": "awaiting_approval" }
```

ユーザーが「v1 の予約リンク判定は現行維持で、表示条件だけ変えて」と返した場合は v1 を編集せず v2 を追加する。

```json
{
  "current_version": "design-v2",
  "status": "awaiting_approval",
  "versions": [
    { "version": "design-v1", "status": "superseded", "supersedes": null },
    { "version": "design-v2", "status": "awaiting_approval", "supersedes": "design-v1" }
  ]
}
```

「v2 で OK」を受けて `approved` へ。worktree を切った時点で全体 status を `implementation_started` にする。

## 承認と認めなかった返答

- 最初の依頼文の「実装して」
- 別 Issue の設計への「OK」
- 「いいね」「なるほど」のような相槌
- `superseded` になった v1 への「これで進めて」（v1 の内容を引き継いだ v3 を作って再提示した）

## 独立レビュー指摘との関係

独立レビューが「候補 0 件のとき fallback 文言を出すべき」と指摘した。これは承認済み設計に存在しない失敗・縮退経路の追加なので `設計差分` として実装を止め、v3 に「候補 0 件の縮退経路」を追加して再承認を得てから実装した。

## 契約 ID を持つ repository での書き方

長期仕様が `PIPE-01`〜`PIPE-11` の契約 ID を定義していたため、AC 表の「対応する仕様・契約 ID」列に ID を入れ、TC は「決定的テスト / live LLM 評価 / 人手評価」の 3 段階に分けた。live 評価だけで遵守を主張しないことを AC に書いた。
