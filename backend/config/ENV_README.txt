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

■ SCALE_LOT_SIZE
AIがSCALEを返した際に追加するロット数。デフォルトは0.5。

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

■ MIN_RRR
  期待値計算において許容する最小リスクリワード比。TP候補の中から、
  確率×pips が最大となり MIN_RRR 以上のものを採用する。

■ ENFORCE_RRR
  true にするとエントリー時のTP/SLが MIN_RRR を下回らないよう強制調整
  される。調整後の値は INFO レベルでログ出力される。
  MIN_RRR=1.2、ENFORCE_RRR=true が推奨設定。


# 以下は README に記載されていた追加の環境変数

- RANGE_CENTER_BLOCK_PCT: ADX が ADX_RANGE_THRESHOLD 以下のとき、BB 中心付近のエントリーをどの程度ブロックするか (0.3 = 30%)
- BAND_WIDTH_THRESH_PIPS: BB 幅がこの値未満になると自動的にレンジモードに切り替える
- AI_PROFIT_TRIGGER_RATIO: TP 目標の何割到達で AI に利確を問い合わせるか
- MIN_RRR: 最低許容リスクリワード比
- ENFORCE_RRR: true にすると MIN_RRR を下回らないよう TP/SL を調整
- STAGNANT_EXIT_SEC: 利益が伸びないまま停滞したと判断するまでの秒数
- STAGNANT_ATR_PIPS: ATR がこの値以下のとき停滞判定を行う
- MIN_HOLD_SEC: ポジションを最低何秒保持するか
- REVERSAL_EXIT_ATR_MULT / REVERSAL_EXIT_ADX_MIN: 反対側 BB を終値で超えた際の早期撤退条件
- POLARITY_EXIT_THRESHOLD: ポラリティによる早期決済を行う閾値
- PULLBACK_LIMIT_OFFSET_PIPS: 指値エントリーへ切り替える際の基本オフセット
- AI_LIMIT_CONVERT_MODEL: 指値を成行に変換するか判断する AI モデル
- PULLBACK_PIPS: ピボット抑制中に使用するオフセット
- PIP_SIZE: 通貨ペアの1pip値 (JPYペアは 0.01 など)
- TRADE_TIMEFRAMES: 取得するローソク足のタイムフレーム一覧
- TP_BB_RATIO: ボリンジャーバンド幅からTP候補を算出するときの倍率
- RANGE_ENTRY_OFFSET_PIPS: BB 中心からこのpips以内なら LIMIT へ切替
- NOISE_SL_MULT: AI計算のSLを拡大する倍率
- PATTERN_NAMES: 検出対象とするチャートパターン名一覧
- LOCAL_WEIGHT_THRESHOLD: ローカル検出とAI判定の重み付け閾値
- PATTERN_MIN_BARS / PATTERN_TOLERANCE: パターン成立条件の細かい調整
- PATTERN_EXCLUDE_TFS / PATTERN_TFS: チャートパターン検出を行う/除外する時間足
- STRICT_ENTRY_FILTER: M1 RSI クロス必須判定のオン/オフ
- HIGHER_TF_ENABLED: 上位足ピボットをTP計算に利用するか

# 分割エントリー関連設定

- SCALE_LOT_SIZE: 追加エントリー時のロット数
- SCALE_MAX_POS: 追加エントリーの最大回数
- SCALE_TRIGGER_ATR: 追加エントリー発動ATR倍率

## 設定例

```
SCALE_LOT_SIZE=0.3
SCALE_MAX_POS=2
SCALE_TRIGGER_ATR=0.5
```

