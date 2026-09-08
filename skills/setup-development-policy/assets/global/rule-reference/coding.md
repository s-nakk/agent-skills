# Codex 共通コーディング規約

共通 `AGENTS.md` の補助規約。コード・API・DB・設定の設計、実装、レビューに着手する前に読む。

## Engineering standards

- IMPORTANT: Do not write overly defensive code. Always prefer simplicity over pathological complexity.
- TypeScript で新しい `any` を追加しない。外部入力や未検証値には `unknown` を使い、schema validation、type guard、narrowing を経てから利用する
- class は、identity、state、lifecycle、framework contract が必要な場合に限る。純粋な変換や手続きは関数と明示的な型を優先する
- 意味の説明できない数値や文字列を直書きしない。環境差、secret、運用調整値は型付き設定へ置き、domain invariant は名前付き定数としてコードの近くに置く
- コメントは「なぜ」を補うために書き、コードの言い換えを避ける。日本語コメントは句点（`。`）で終えない
- TypeScript の公開 API は必要に応じて TSDoc または JSDoc、C# の公開 API は必要に応じて XML documentation を使う。自明な内部メソッドへ形式的な説明を量産しない
- `<input type="date">` には `max="9999-12-31"` を指定する

## 互換性と耐障害性

- 根拠のない旧形式併存、deprecated alias、dual-write、旧 API への silent fallback を追加しない
- 変更前に、実 deploy、利用者、保存済みデータ、公開仕様から対象契約の release status を確認する
- 未リリースと確認できた契約は、call site とデータを前方移行し、旧経路を削除する
- リリース済み契約は、互換期間、データ移行、deploy 順序、rollback を設計してから変更する
- 入力検証、欠損値の明示処理、retry、timeout、circuit breaker、障害時の縮退は互換 shim ではない。現行契約と障害モデルに基づいて設計する
