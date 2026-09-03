# 前回finding

`group_subject_indices` は同じPRのschemaで必須なのに、parserが欠落を空配列として受理している。
schema整合のため欠落を構造エラーとして拒否すること。
