# entry_signal の使い方

`entry_signal` 関数は ADX 値からスキャルプ・トレンドフォローを
自動的に切り替えるシンプルなユーティリティです。主な環境変数は
次の 2 つです。

- `ADX_SCALP_MIN` … この値以上で `scalp` モードとなります
- `ADX_TREND_MIN` … この値以上で `trend_follow` モードとなります

デフォルトではそれぞれ 20、30 に設定されています。閾値を変更
したい場合は `backend/config/settings.env` で上書きしてください。

```
ADX_SCALP_MIN=25
ADX_TREND_MIN=40
```

これらを変更後にモジュールを再読み込みすると `choose_strategy`
の判定基準も自動的に切り替わります。
