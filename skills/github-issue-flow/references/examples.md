# 実例（匿名化済み）

## 変更ゲートで止めた例

依頼: 「#412 を実装して、終わったら Issue も閉じて」

- `実装して` は Issue 変更の許可ではない。`Issue も閉じて` は対象 Issue（#412）、操作（close）、目的（完了）の 3 点が揃っているので、PR merge 後にユーザーへ確認したうえで close する
- PR 本文には `Refs #412`。自動 close の `Closes #412` は「merge 時に自動で閉じて」と明示されていないので使わない

依頼: 「#480 の調査結果を Issue に追記しておいて」

- 対象 Issue（#480）、操作（comment 追加）、値（調査結果）が揃うので comment を 1 回だけ追加する
- 追記後にさらに修正したくなっても、再度の明示指示なしに edit しない

## PR 本文の例

```markdown
## 概要

Refs #412

問い合わせ一覧で担当者を絞り込んだ後にページを移動すると、絞り込みが外れて全件表示に戻っていました。移動後も絞り込みを保持するようにしました。

## 原因

ページ番号を変える操作が、絞り込み条件を URL に含めずに再読み込みしていました。

## 対応

- ページ移動時に担当者の絞り込み条件を引き継ぐ
- 絞り込み条件が URL に残るため、リンク共有でも同じ表示になる

## 検証

- `pnpm --filter web test inquiries` → 12 passed
- `pnpm --filter web lint` → warning 0
- 独立レビュー → head `9f3c1a2`、blocker 0 件

## 補足

staging 未反映。本番反映のタイミングは別途相談。
```

## Completion report の例

```text
Issue #412 の修正を draft PR #418 にまとめました。
- ブランチ: fix/issue-412-inquiry-filter、commit 9f3c1a2
- 変更: 問い合わせ一覧の絞り込みがページ移動で外れる不具合を修正
- 検証: 上記 PR 本文のとおり
- 独立レビュー: head 9f3c1a2 で blocker なし
- Issue 紐づけ: PR 本文に Refs #412 あり。timeline の cross-reference も確認
- Issue の変更: なし
```
