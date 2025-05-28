# =========================
# settings.env 説明ファイル
# =========================

■ DEFAULT_PAIR
取引対象とする通貨ペア（例: USD_JPY）

■ INITIAL_TP_PIPS / INITIAL_SL_PIPS
初期の利確（TP）・損切り（SL）幅（単位: pips）
※AIがこれを上書きする可能性あり

■ AI_MODEL
利用するOpenAIモデル名（gpt-4-turbo / gpt-4oなど）

■ RSI_PERIOD
RSI指標の計算期間。一般的には14が標準。

■ EMA_PERIOD
EMA（指数平滑移動平均）の計算期間。

■ ATR_PERIOD
ATR（ボラティリティ指標）の計算期間。

■ BOLLINGER_WINDOW / BOLLINGER_STD
ボリンジャーバンドの移動平均期間と標準偏差設定。

■ TRADE_LOT_SIZE
1トレードで使用するロットサイズ（1 = 1000通貨）

■ フィルター設定（AI呼び出し制御用）

- RSI_ENTRY_LOWER / RSI_ENTRY_UPPER:
  RSIがこの範囲にある時だけエントリーフィルターを通過

- ATR_ENTRY_THRESHOLD:
  ATR（ボラティリティ）がこの値より大きいときだけAI判断を許可

- EMA_DIFF_THRESHOLD:
  価格とEMAの乖離率がこの値を超えるとトレンド発生と判断

- BB_POSITION_THRESHOLD:
  ボリンジャーバンドの上限・下限に対する価格の相対位置（0〜1）をしきい値とする

- OVERSHOOT_ATR_MULT:
  BB下限をATR×この倍率だけ下回った場合はエントリーをブロック
- REVERSAL_EXIT_ATR_MULT / REVERSAL_EXIT_ADX_MIN:
  価格がボリンジャーバンドの反対側を終値で越えた際、
  差分がATR×REVERSAL_EXIT_ATR_MULT以上でADXがREVERSAL_EXIT_ADX_MIN
  以上なら早期決済を検討
- NOISE_SL_MULT:
  AIが算出したSLをこの倍率で拡大

■ トレーリングストップ設定

- TRAIL_ENABLED:
  トレーリングストップ機能のオン/オフ。

- TRAIL_TRIGGER_PIPS / TRAIL_DISTANCE_PIPS:
  ATRが取得できない場合に使用する固定幅（pips）。
  利益からTRAIL_DISTANCE_PIPSを引いた値が0以下の場合、
  トレーリングストップは発注されず警告のみが出ます。
  TRAIL_TRIGGER_PIPSはTRAIL_DISTANCE_PIPS以上に設定することを推奨します。

- TRAIL_TRIGGER_MULTIPLIER / TRAIL_DISTANCE_MULTIPLIER:
  ATR値を基準にした倍率。ATRが利用可能なときは
  発動条件 = ATR × TRAIL_TRIGGER_MULTIPLIER、
  距離 = ATR × TRAIL_DISTANCE_MULTIPLIER で計算される。

■ チャートパターン検出設定

- PATTERN_MIN_BARS:
  パターン完成判定に必要な最小ローソク足本数。デフォルトは5本。

- PATTERN_TOLERANCE:
  高値・安値の許容誤差。デフォルトは0.005。
- PATTERN_EXCLUDE_TFS:
  ここで指定したタイムフレーム (例: M1) はパターン検出から除外される。

- ADX_NO_TRADE_MIN / ADX_NO_TRADE_MAX:
  ADXがこの範囲に収まっているとエントリーを見送る。

