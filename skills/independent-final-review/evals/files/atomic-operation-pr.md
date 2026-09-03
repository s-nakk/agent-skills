# 変更前契約とPR差分

リリース済み仕様 `ADMIN-BULK-03` は、営業時間の一括置換を全行一つのtransactionで扱い、全行validation成功時だけcommitすると定めています。

PRはvalidation errorを行番号付きで返すよう改善しますが、1行でも不正ならtransaction全体をrollbackする契約を維持します。

混在fixture:

- 月曜 `09:00-18:00` は有効
- 火曜 `18:00-09:00` は不正
- 水曜 `09:00-18:00` は有効

testはHTTP 422、火曜のerror、全曜日が未更新であることをassertします。
