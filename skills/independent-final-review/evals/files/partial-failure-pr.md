# PRの差分

同じPRで `group_subject_indices` をschemaの必須fieldとして新設し、仕様書も必須へ更新しています。

parserは一つでもfield欠落があると `UnderstandingFailure.Structural` を返し、call siteは質問理解全体をfallback回答へ送ります。

追加testは、単一グループでfieldが欠落した時に構造失敗となることだけをassertしています。
次のfixtureはありません。

```json
{
  "question_groups": [
    { "question": "A院とB院は提携していますか" },
    { "question": "支払い方法を教えて", "group_subject_indices": [] }
  ]
}
```
