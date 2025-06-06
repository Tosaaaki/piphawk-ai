# decide_trade_mode の概要

`decide_trade_mode` は ATR、ADX、出来高平均の三指標を0〜1に正規化し、平均スコアで市況を判定します。スコアが 0.66 以上なら `trend_follow`、0.33 以下なら `scalp_momentum` となり、その中間は直前のモードを維持します。

主な環境変数は次の通りです。

- `MODE_ATR_PIPS_MIN` / `MODE_BBWIDTH_PIPS_MIN` … ボラティリティ判定に使う閾値
- `MODE_EMA_SLOPE_MIN` / `MODE_ADX_MIN` … モメンタム判定のしきい値
- `MODE_VOL_MA_MIN` … 流動性判定に使う出来高平均
- `MODE_ATR_QTL` / `MODE_ADX_QTL` … 過去データから算出するATR・ADXの分位点
- `MODE_QTL_LOOKBACK` … 上記計算に使う本数 (デフォルト20)
- `HTF_SLOPE_MIN` … 上位足EMA傾きチェックのしきい値
- `TREND_ENTER_SCORE` / `SCALP_ENTER_SCORE` … モード切替に使う基準値
- `TREND_HOLD_SCORE` / `SCALP_HOLD_SCORE` … ヒステリシス用の維持しきい値
