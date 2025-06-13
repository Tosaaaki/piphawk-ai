# decide_trade_mode の概要

`decide_trade_mode` は ATR、ADX、DI 差、EMA 傾き、出来高を各 0〜2 点でスコア化し、合計点を正規化して市況を判定します。指標が強ければ 2 点、基準を満たせば 1 点と段階的に加算されます。スコアが 0.66 以上なら `trend_follow`、0.33 以上なら `scalp_momentum` となり、それ未満は直前のモードを維持します。

このロジックは `analysis.detect_mode()` として公開され、戻り値にはモード、スコア、理由をまとめた `MarketContext` クラスを使用します。LLM を介さないため高速かつ再現性のある判定が可能です。

主な環境変数は次の通りです。

- `MODE_ATR_PIPS_MIN` / `MODE_BBWIDTH_PIPS_MIN` … ボラティリティ判定に使う閾値
- `MODE_EMA_SLOPE_MIN` / `MODE_ADX_MIN` … モメンタム判定のしきい値
- `MODE_DI_DIFF_MIN` / `MODE_DI_DIFF_STRONG` … +DIと−DIの差を評価する閾値
- `MODE_VOL_RATIO_MIN` / `MODE_VOL_RATIO_STRONG` … 出来高と平均の比率評価に使用
- `MODE_VOL_MA_MIN` … 流動性判定に使う出来高平均
- `MODE_ATR_QTL` / `MODE_ADX_QTL` … 過去データから算出するATR・ADXの分位点
- `MODE_QTL_LOOKBACK` … 上記計算に使う本数 (デフォルト20)
- `HTF_SLOPE_MIN` … 上位足EMA傾きチェックのしきい値
- `TREND_ENTER_SCORE` / `SCALP_ENTER_SCORE` … モード切替に使う基準値
- `TREND_HOLD_SCORE` / `SCALP_HOLD_SCORE` … ヒステリシス用の維持しきい値
- `MODE_STRONG_TREND_THRESH` … 強トレンド判定に使うスコア閾値
- `MODE_BONUS_START_JST` / `MODE_BONUS_END_JST` … トレンド寄りに補正する時間帯
- `MODE_PENALTY_START_JST` / `MODE_PENALTY_END_JST` … スキャルプ寄りに補正する時間帯

`SCALP_ENTER_SCORE` と `SCALP_HOLD_SCORE` は、スコアリング結果から
`scalp_momentum` モードへ切り替える際の閾値と、維持を判断する下限値です。
デフォルトはそれぞれ `0.20` と `0.15` で、値を下げるほどスキャルプへ
移行しやすくなります。

`RANGE_ADX_MIN` は ADX がこの値を下回った場合にレンジ判定カウンターを
増やします。連続 `RANGE_ADX_COUNT` 回に達するとモードを
`scalp_momentum` へ切り替えます。推奨値は `15` です。

`SCALP_AI_BBWIDTH_MAX` は旧仕様で、現在は 0 (制限なし) が推奨値です。

モード判定に用いる閾値は `config/mode_detector.yml` にまとめることもできます。
ファイルが存在すると `analysis.mode_detector.load_config()` が自動で読み込み、
環境変数よりも優先されます。
