# 差分再レビュー対象

parserを変更し、いずれかの質問グループで `relation_subject_indices` が欠落すると質問理解全体を `UnderstandingFailure.Structural` にします。
call siteは構造失敗時に候補選定を行わず、定型fallback回答を返します。

追加testは単一グループ欠落だけです。
グループ0が欠落、グループ1が有効でFAQ-204へ一致する混在fixtureはありません。
