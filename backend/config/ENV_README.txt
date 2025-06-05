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

■ MIN_TRADE_LOT / MAX_TRADE_LOT
1トレードで許可される最小ロット数と最大ロット数
単位はLot（1 Lot = 1000通貨）

■ SCALE_LOT_SIZE
AIがSCALEを返した際に追加するロット数。デフォルトは0.5。

■ AI_COOLDOWN_SEC
 AI呼び出しの基本クールダウン時間。デフォルトは 30 秒。

■ AI_COOLDOWN_SEC_OPEN / AI_COOLDOWN_SEC_FLAT / AI_REGIME_COOLDOWN_SEC
 AI呼び出しの最小間隔（秒）を個別に設定する。OPENはポジション保有時、FLATはノーポジ時、REGIMEはトレンド判定用。デフォルトは OPEN=60、FLAT=30、REGIME=20。

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

- ENABLE_RANGE_ENTRY:
  true にするとレンジ相場でもエントリーを許可し、ADXノートレード判定をスキップする。

■ MIN_RRR
  期待値計算において許容する最小リスクリワード比。TP候補の中から、
  確率×pips が最大となり MIN_RRR 以上のものを採用する。

■ ENFORCE_RRR
  true にするとエントリー時のTP/SLが MIN_RRR を下回らないよう強制調整
  される。調整後の値は INFO レベルでログ出力される。
  MIN_RRR=1.2、ENFORCE_RRR=true が推奨設定。

■ MIN_RRR_AFTER_COST
  スプレッドやスリッページなどコスト控除後のRRRが
  この値以上でなければエントリーを行わない。
  デフォルトは 0 (チェック無効)。

■ ENTRY_SLIPPAGE_PIPS
  エントリー時に想定するスリッページ幅(pips)。
  MIN_RRR_AFTER_COST の計算に利用される。


# 以下は README に記載されていた追加の環境変数

- RANGE_CENTER_BLOCK_PCT: ADX が ADX_RANGE_THRESHOLD 以下のとき、BB 中心付近のエントリーをどの程度ブロックするか (0.3 = 30%)
- BAND_WIDTH_THRESH_PIPS: BB 幅がこの値未満になると自動的にレンジモードに切り替える
- AI_PROFIT_TRIGGER_RATIO: TP 目標の何割到達で AI に利確を問い合わせるか
- MIN_RRR: 最低許容リスクリワード比
- ENFORCE_RRR: true にすると MIN_RRR を下回らないよう TP/SL を調整
- MIN_RRR_AFTER_COST: スプレッド控除後のRRR下限
- ENTRY_SLIPPAGE_PIPS: エントリー時の想定スリッページ
- STAGNANT_EXIT_SEC: 利益が伸びないまま停滞したと判断するまでの秒数
- STAGNANT_ATR_PIPS: ATR がこの値以下のとき停滞判定を行う
- MIN_HOLD_SECONDS: ポジションを最低何秒保持するか
- REVERSAL_EXIT_ATR_MULT / REVERSAL_EXIT_ADX_MIN: 反対側 BB を終値で超えた際の早期撤退条件
- REVERSAL_RSI_DIFF: M5 と M15 の RSI 差分がこの値以上で MACD ヒストグラムが同じ方向ならエントリーをブロック
- POLARITY_EXIT_THRESHOLD: ポラリティによる早期決済を行う閾値
- PULLBACK_LIMIT_OFFSET_PIPS: 指値エントリーへ切り替える際の基本オフセット
- AI_LIMIT_CONVERT_MODEL: 指値を成行に変換するか判断する AI モデル
- PULLBACK_PIPS: ピボット抑制中に使用するオフセット
- PULLBACK_ATR_RATIO: ATR 比で待機するプルバック深度の倍率
- BYPASS_PULLBACK_ADX_MIN: ADX がこの値以上ならプルバック待ちをスキップ
- ALLOW_NO_PULLBACK_WHEN_ADX: ADX がこの値以上ならプルバック不要とプロンプトに明記
- EXT_BLOCK_ATR: 終値が EMA20 からこの倍率 × ATR 以上乖離しているとエントリー禁止
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
- VOL_MA_PERIOD: 出来高平均を計算する期間
- MIN_VOL_MA / MIN_VOL_M1: ボリュームフィルタの最小値
- ADX_SLOPE_LOOKBACK: ADX の傾き計算に使う本数
- ADX_DYNAMIC_COEFF: BB 幅によって ADX しきい値を補正する係数
- COMPOSITE_MIN: ADXとBB幅から算出するComposite Trend Scoreのしきい値
- EMA_FLAT_PIPS: EMA の傾きをフラットとみなす幅
- OVERSHOOT_ATR_MULT: BB下限をATR×この倍率だけ割り込むとエントリーをブロック
- REV_BLOCK_BARS / TAIL_RATIO_BLOCK / VOL_SPIKE_PERIOD:
  Recent Candle Bias フィルターで参照する設定。直近のローソク足本数、ヒゲ比率、出来高急増判定期間を指定する。
  デフォルトは 3 / 2.0 / 5。
- VOL_SPIKE_ADX_MULT / VOL_SPIKE_ATR_MULT: BB幅がしきい値を下回っていても、ADXまたはATRがこの倍率で急拡大した場合は成行エントリーに切り替える
- STRICT_TF_ALIGN: マルチTF整合が取れない場合のキャンセル可否
- ALIGN_STRICT: 上記と同義のエイリアス
- TF_EMA_WEIGHTS: 上位足EMA整合の重み付け (例 `M5:0.4,H1:0.3,H4:0.3`)
- AI_ALIGN_WEIGHT: AIの方向性をEMA整合に加味する重み
- ALIGN_BYPASS_ADX: M5 ADXがこの値以上でAI方向が設定されている場合、整合チェックをスキップ
- LT_TF_PRIORITY_ADX: 下位足ADXがこの値以上でEMAクロスが発生したら他タイムフレームの重みを減少
- LT_TF_WEIGHT_FACTOR: 上記条件を満たした際に適用する重み係数 (0.5なら半減)

- LINE_CHANNEL_TOKEN: LINE 通知に使用するチャンネルアクセストークン
- LINE_USER_ID: 通知を送るユーザーのLINE ID

# 分割エントリー関連設定

- SCALE_LOT_SIZE: 追加エントリー時のロット数
 - SCALE_MAX_POS: 1ポジションにつき許可する追加回数
 - SCALE_TRIGGER_ATR: エントリー価格からの乖離が `ATR × この値` を超えたときのみ追加

## 設定例

```
SCALE_LOT_SIZE=0.3
SCALE_MAX_POS=2
SCALE_TRIGGER_ATR=0.5
```

## 新規追加設定

- ATR_MULT_TP / ATR_MULT_SL: ATR(M5) に掛ける TP, SL の倍率
- BLOCK_COUNTER_TREND: M15/H1 が同方向のとき逆張りをブロック
- COUNTER_BYPASS_ADX: M5 ADX がこの値以上かつ同方向なら逆張り判定を無視
- BLOCK_ADX_MIN: ADX がこの値以上で上昇中なら逆張りを抑制
- COUNTER_TREND_TP_RATIO: 逆張りを許容する際にTPをこの倍率で縮小
- CLIMAX_ENABLED: クライマックス検出による自動エントリーを有効化
- CLIMAX_ZSCORE: ATR Z スコアの閾値
- CLIMAX_TP_PIPS / CLIMAX_SL_PIPS: クライマックス時に使用する TP/SL
- ALLOW_DELAYED_ENTRY: トレンドが過熱している場合に "wait" を返させ、押し目到来で再問い合わせする
- TREND_ADX_THRESH: トレンド判定に用いるADXの基準値。プロンプトの条件とローカル判定で参照される
- MIN_EARLY_EXIT_PROFIT_PIPS: 早期撤退を検討する際に必要な最低利益幅
- SCALP_MODE: スキャルピング用の固定TP/SLエントリーを有効化
- SCALP_ADX_MIN: SCALP_MODE時に必要な最小ADX
- SCALP_TP_PIPS / SCALP_SL_PIPS: スキャル時のTP/SL幅
- SCALP_COND_TF: スキャルプ時に市場判定へ使う時間足 (デフォルト M1)
- H1_BOUNCE_RANGE_PIPS: H1安値/高値からこのpips以内ならエントリーを見送る
■ OANDA_MATCH_SEC
  ローカルトレードと OANDA 取引を照合するときの許容秒数。デフォルトは60秒。

