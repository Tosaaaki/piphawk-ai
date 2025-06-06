# decide_trade_mode の概要

`decide_trade_mode` は ATR とボリンジャーバンド幅、EMA や MACD と ADX、そして出来高平均の三要素から市況を判定します。各カテゴリの条件を 2 つ以上満たすと `trend_follow`、そうでなければ `scalp` を返します。

主な環境変数は次の通りです。

- `MODE_ATR_PIPS_MIN` / `MODE_BBWIDTH_PIPS_MIN` … ボラティリティ判定に使う閾値
- `MODE_EMA_SLOPE_MIN` / `MODE_ADX_MIN` … モメンタム判定のしきい値
- `MODE_VOL_MA_MIN` … 流動性判定に使う出来高平均
