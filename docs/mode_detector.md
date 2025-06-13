# モード判定ロジックまとめ

本稿では `signals.composite_mode.decide_trade_mode()` を中心とした指標スコアリング方式について解説します。LLM へ問い合わせることなく、市況を **scalp_momentum** / **trend_follow** / **range** に分類します。

## スコアリング項目

- **ボラティリティ**: `ATR` とボリンジャーバンド幅を比較し、`MODE_ATR_PIPS_MIN` や `MODE_BBWIDTH_PIPS_MIN` を超えたかで 0〜2 点を付与します。
- **モメンタム**: `ADX` 値と `EMA` 傾きが `MODE_ADX_MIN`、`MODE_EMA_SLOPE_MIN` を満たすか判定します。`DI` 差(`MODE_DI_DIFF_MIN`, `MODE_DI_DIFF_STRONG`) も加点要素です。
- **出来高**: `MODE_VOL_RATIO_MIN`、`MODE_VOL_RATIO_STRONG` を基準に、平均比をスコア化します。流動性が足りない場合は `MODE_VOL_MA_MIN` を参照します。
- **上位足確認**: `HTF_SLOPE_MIN` を超えるかで、より長期のトレンド整合性を評価します。

各項目を合計し、スコアが `TREND_ENTER_SCORE` 以上なら `trend_follow`、`SCALP_ENTER_SCORE` 以上なら `scalp_momentum` へ移行します。現在のモード維持には `TREND_HOLD_SCORE`、`SCALP_HOLD_SCORE` を利用します。

## パラメータ調整

環境変数や YAML で閾値を変更できます。主な変数は以下の通りです。

- `MODE_ATR_PIPS_MIN` / `MODE_BBWIDTH_PIPS_MIN`
- `MODE_EMA_SLOPE_MIN` / `MODE_ADX_MIN`
- `MODE_DI_DIFF_MIN` / `MODE_DI_DIFF_STRONG`
- `MODE_VOL_RATIO_MIN` / `MODE_VOL_RATIO_STRONG`
- `MODE_VOL_MA_MIN`
- `MODE_ATR_QTL` / `MODE_ADX_QTL`
- `MODE_QTL_LOOKBACK`
- `HTF_SLOPE_MIN`
- `TREND_ENTER_SCORE` / `SCALP_ENTER_SCORE`
- `TREND_HOLD_SCORE` / `SCALP_HOLD_SCORE`

閾値を下げるほどモード切り替えが早くなるため、過去データを用いて勝率や平均リワードを確認しながら調整してください。
