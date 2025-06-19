# Environment Variables

### DEFAULT_PAIR

取引対象とする通貨ペア（例: USD_JPY）

### TRADES_DB_PATH

取引履歴を保存するSQLiteファイルのパス。デフォルトではプロジェクトルートの
`trades.db` を利用し、Docker環境では `/app/backend/logs/trades.db` が使用されます。
環境変数 `TRADES_DB_PATH` で別のパスを指定できます。

### INITIAL_TP_PIPS / INITIAL_SL_PIPS

初期の利確（TP）・損切り（SL）幅（単位: pips）
※AIがこれを上書きする可能性あり

### AI_MODEL

利用するOpenAIモデル名（gpt-4.1-nano など）

### GPT model variants

- AI_REGIME_MODEL: トレンド判定に使用するモデル
- AI_ENTRY_MODEL: エントリー判断用モデル
- AI_EXIT_MODEL: エグジット判断用モデル
- AI_TRADE_MODEL: 取引全般を扱う統合モデル
- AI_SCALP_MODEL: スキャルピング専用モデル
- AI_LIMIT_CONVERT_MODEL: 指値を成行に変換するか判定するモデル
- AI_PATTERN_MODEL: チャートパターン検出用モデル

### RSI_PERIOD

RSI指標の計算期間。一般的には14が標準。

### EMA_PERIOD

EMA（指数平滑移動平均）の計算期間。

### ATR_PERIOD

ATR（ボラティリティ指標）の計算期間。

### ADX_PERIOD

ADX 指標の計算に用いる期間。デフォルトは12。

### BOLLINGER_WINDOW / BOLLINGER_STD

ボリンジャーバンドの移動平均期間と標準偏差設定。

### MIN_TRADE_LOT / MAX_TRADE_LOT

1トレードで許可される最小ロット数と最大ロット数
単位はLot（1 Lot = 1000通貨）

### SCALE_LOT_SIZE

AIがSCALEを返した際に追加するロット数。デフォルトは0.5。

### AI_COOLDOWN_SEC_OPEN / AI_COOLDOWN_SEC_FLAT / AI_REGIME_COOLDOWN_SEC

 AI呼び出しの最小間隔（秒）を個別に設定する。OPENはポジション保有時、FLATはノーポジ時、REGIMEはトレンド判定用。デフォルトは OPEN=60、FLAT=60、REGIME=60。

### AI_COOLDOWN_HIGH_VOL_MULT

 `is_high_vol_session()` が `true` を返す時間帯は、上記クールダウン秒数にこの倍率を掛ける。デフォルトは `0.5` で半分に短縮される。

### フィルター設定（AI呼び出し制御用）

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
- OVERSHOOT_DYNAMIC_COEFF:
  BB幅に応じて上記倍率を補正する係数。0なら補正なし
- OVERSHOOT_BASE_MULT:
  Overshoot 検出直後に適用するATR倍率。デフォルトは0.5。
- OVERSHOOT_MAX_MULT:
  時間経過により上限となるATR倍率。デフォルトは0.7。
- OVERSHOOT_RECOVERY_RATE:
  Overshoot検出後、1分ごとに倍率をどれだけ緩和するか。
- OVERSHOOT_MAX_PIPS:
  Overshoot判定に使う最大許容幅（pips）。0なら無効。
- OVERSHOOT_DYNAMIC:
  trueならATR連動で許容幅を自動計算。
- OVERSHOOT_FACTOR:
  ATR連動時の倍率。許容幅 = ATR × この値。
- OVERSHOOT_FLOOR / OVERSHOOT_CEIL:
  自動計算した許容幅の下限・上限。
- OVERSHOOT_MODE:
  warnを指定するとOvershoot検出時に警告のみで通過する。
- OVERSHOOT_WINDOW_CANDLES:
  直近のローソク足を何本参照してOvershoot幅を判定するか。
  Overshoot平均を計算するローソク足本数。例: 3 なら直近3本の終値平均で判定。
- REVERSAL_EXIT_ATR_MULT / REVERSAL_EXIT_ADX_MIN:
  価格がボリンジャーバンドの反対側を終値で越えた際、
  差分がATR×REVERSAL_EXIT_ATR_MULT以上でADXがREVERSAL_EXIT_ADX_MIN
  以上なら早期決済を検討
- NOISE_SL_MULT:
  AIが算出したSLをこの倍率で拡大
- TP_ONLY_NOISE_MULT:
  SLが想定ノイズ×この倍率より小さい場合は TP のみを設定

### トレーリングストップ設定

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
- TRAIL_AFTER_TP:
  true にするとTP到達後、建値にATR×0.3の距離で
  トレーリングストップを設定する。デフォルトはfalse。

### チャートパターン検出設定

- PATTERN_MIN_BARS:
  パターン完成判定に必要な最小ローソク足本数。デフォルトは5本。

- PATTERN_TOLERANCE:
  高値・安値の許容誤差。デフォルトは0.005。
- PATTERN_EXCLUDE_TFS:
  ここで指定したタイムフレーム (例: M1) はパターン検出から除外される。

- ADX_NO_TRADE_MIN / ADX_NO_TRADE_MAX:
  ADXがこの範囲に収まっているとエントリーを見送る。USD/JPYでは
  15〜18程度が目安。0を指定すればこの判定を無効化できる。

- COOL_BBWIDTH_PCT:
  5分足ボリンジャーバンド幅 ÷ ATR がこの値未満ならエントリーを控える。
  0を指定すると無効化できる。
- COOL_ATR_PCT:
  ATR がこの値未満のときエントリーを控える。0を指定すると無効化。

- ENABLE_RANGE_ENTRY:
  true にするとレンジ相場でもエントリーを許可し、ADXノートレード判定をスキップする。

### MIN_RRR

  期待値計算において許容する最小リスクリワード比。TP候補の中から、
  確率×pips が最大となり MIN_RRR 以上のものを採用する。

### ENFORCE_RRR

  true にするとエントリー時のTP/SLが MIN_RRR を下回らないよう強制調整
  される。調整後の値は INFO レベルでログ出力される。
  MIN_RRR=1.2、ENFORCE_RRR=true が推奨設定。

### MIN_RRR_AFTER_COST

  スプレッドやスリッページなどコスト控除後のRRRが
  この値以上でなければエントリーを行わない。
  デフォルトは 0 (チェック無効)。

### ENTRY_SLIPPAGE_PIPS

  エントリー時に想定するスリッページ幅(pips)。
  MIN_RRR_AFTER_COST の計算に利用される。

### MIN_NET_TP_PIPS

  スプレッド控除後に許容される最小TP幅(pips)。デフォルトは1。

### DYN_TP_PROB_FLOOR / DYN_TP_PROB_CEIL

  `noise_pips` を用いて算出される動的な TP 達成確率の下限値・上限値を設定
  する。計算式は `dynamic_min_tp_prob = max(DYN_TP_PROB_FLOOR, noise_pips * 0.6)`
  で求めた値を DYN_TP_PROB_CEIL 以下に切り詰める。
  DYN_TP_PROB_FLOOR のデフォルトは 0.55、DYN_TP_PROB_CEIL のデフォルトは
  MIN_TP_PROB。

# 以下は README に記載されていた追加の環境変数

- RANGE_CENTER_BLOCK_PCT: ADX が ADX_RANGE_THRESHOLD 以下のとき、BB 中心付近のエントリーをどの程度ブロックするか (0.3 = 30%)
- BAND_WIDTH_THRESH_PIPS: BB 幅がこの値未満になると自動的にレンジモードに切り替える
- AI_PROFIT_TRIGGER_RATIO: TP 目標の何割到達で AI に利確を問い合わせるか
- MAX_AI_EXIT_CALLS: 1ポジションあたり propose_exit_adjustment を呼び出す上限回数
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
- HIGH_ATR_PIPS / LOW_ADX_THRESH: ATRがHIGH_ATR_PIPS以上でADXがLOW_ADX_THRESH未満の場合に早期撤退
- PULLBACK_LIMIT_OFFSET_PIPS: 指値エントリーへ切り替える際の基本オフセット
- AI_LIMIT_CONVERT_MODEL: 指値を成行に変換するか判断する AI モデル
- PULLBACK_PIPS: ピボット抑制中に使用するオフセット
- PULLBACK_ATR_RATIO: ATR 比で待機するプルバック深度の倍率
- BYPASS_PULLBACK_ADX_MIN: ADX がこの値以上ならプルバック待ちをスキップ
- ALLOW_NO_PULLBACK_WHEN_ADX: ADX がこの値以上ならプルバック不要とプロンプトに明記 (推奨 `20`)
- EXT_BLOCK_ATR: 終値が EMA20 からこの倍率 × ATR 以上乖離しているとエントリー禁止
- PIP_SIZE: 通貨ペアの1pip値 (JPYペアは 0.01 など)
- TRADE_TIMEFRAMES: 取得するローソク足のタイムフレーム一覧
- TP_BB_RATIO: ボリンジャーバンド幅からTP候補を算出するときの倍率
- RANGE_ENTRY_OFFSET_PIPS: BB 中心からこのpips以内なら LIMIT へ切替
- NOISE_SL_MULT: AI計算のSLを拡大する倍率
- TP_ONLY_NOISE_MULT: SL がノイズより小さい場合に TP のみを設定する倍率
- PATTERN_NAMES: 検出対象とするチャートパターン名一覧
- LOCAL_WEIGHT_THRESHOLD: ローカル検出とAI判定の重み付け閾値
- PATTERN_MIN_BARS / PATTERN_TOLERANCE: パターン成立条件の細かい調整
- PATTERN_EXCLUDE_TFS / PATTERN_TFS: チャートパターン検出を行う/除外する時間足
- STRICT_ENTRY_FILTER: M1 RSI クロス必須判定のオン/オフ
- SCALP_STRICT_FILTER: スキャル時にもクロスを要求するか
- HIGHER_TF_ENABLED: 上位足ピボットをTP計算に利用するか
- VOL_MA_PERIOD: 出来高平均を計算する期間
- MIN_VOL_MA / MIN_VOL_M1: ボリュームフィルタの最小値
- ADX_SLOPE_LOOKBACK: ADX の傾き計算に使う本数
- ADX_DYNAMIC_COEFF: BB 幅によって ADX しきい値を補正する係数
- COMPOSITE_MIN: ADXとBB幅から算出するComposite Trend Scoreのしきい値。デフォルトは`0.2`で、値を下げるとエントリー判定が緩くなる。
- MODE_ATR_PIPS_MIN / MODE_BBWIDTH_PIPS_MIN: トレードモード判定に使うボラティリティ基準
- MODE_EMA_SLOPE_MIN / MODE_ADX_MIN: モメンタム判定のしきい値
- MODE_VOL_MA_MIN: 流動性判定に使う出来高平均
- MODE_ATR_QTL / MODE_ADX_QTL: ATR・ADXの分位点を使ったモード判定割合
- MODE_QTL_LOOKBACK: 分位点計算に用いる過去本数
- HTF_SLOPE_MIN: 上位足EMA傾きチェックのしきい値
- EMA_FLAT_PIPS: EMA の傾きをフラットとみなす幅
- REV_BLOCK_BARS / TAIL_RATIO_BLOCK / VOL_SPIKE_PERIOD:
  Recent Candle Bias フィルターで参照する設定。直近のローソク足本数、ヒゲ比率、出来高急増判定期間を指定する。
  デフォルトは 3 / 2.0 / 5。
- VOL_SPIKE_ADX_MULT / VOL_SPIKE_ATR_MULT: BB幅がしきい値を下回っていても、ADXまたはATRがこの倍率で急拡大した場合は成行エントリーに切り替える
- STRICT_TF_ALIGN: マルチTF整合が取れない場合のキャンセル可否
- ALIGN_STRICT: 上記と同義のエイリアス
- FALLBACK_FORCE_ON_NO_SIDE: AI が "no" と答えたときトレンド方向へエントリーを強制するオプション。使用時は STRICT_TF_ALIGN の影響を受けない。
- TF_EMA_WEIGHTS: 上位足EMA整合の重み付け (例 `M5:0.4,M15:0.2,H1:0.3,H4:0.1`)
- AI_ALIGN_WEIGHT: AIの方向性をEMA整合に加味する重み
- ALIGN_BYPASS_ADX: M5 ADXがこの値以上でAI方向が設定されている場合、整合チェックをスキップ (デフォルト30)
- LT_TF_PRIORITY_ADX: 下位足ADXがこの値以上でEMAクロスが発生したら他タイムフレームの重みを減少
- LT_TF_WEIGHT_FACTOR: 上記条件を満たした際に適用する重み係数 (0.5なら半減)
- ALIGN_ADX_WEIGHT: ADXのDI方向を整合評価へ加える重み
- MIN_ALIGN_ADX: ADXがこの値以上のときのみDI方向を採用
- IGNORE_REGIME_CONFLICT: true でローカルとAIのレジーム衝突チェックを無効化

例:

```bash
LOCAL_WEIGHT_THRESHOLD=0.6
IGNORE_REGIME_CONFLICT=true
```

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
- ALLOW_DELAYED_ENTRY: トレンドが過熱している場合に "wait" を返させ、押し目到来で再問い合わせする (デフォルト `true`)
- TREND_ADX_THRESH: トレンド判定に用いるADXの基準値。プロンプトの条件とローカル判定で参照される
- MIN_EARLY_EXIT_PROFIT_PIPS: 早期撤退を検討する際に必要な最低利益幅
- SCALP_MODE: スキャルプモードを強制したい場合に true/false を指定
- ADX_SCALP_MIN: SCALP_MODE時に必要な最小ADX
- SCALP_SUPPRESS_ADX_MAX: この値を超えるADXではSCALP_MODEをオフにする
- SCALP_TP_PIPS / SCALP_SL_PIPS: ボリンジャーバンドが使えない場合の固定TP/SL幅
- SCALP_COND_TF: スキャルプ時に市場判定へ使う時間足 (デフォルト M1)。
  S10 を指定すると 10 秒足データも取得する
- TREND_COND_TF: トレンドフォロー時に市場判定へ使う時間足 (デフォルト M5)
- SCALP_OVERRIDE_RANGE: true でレンジ判定を無視してスキャルを実行
- HOLD_TIME_MIN / HOLD_TIME_MAX: ATR から計算した保持時間の下限・上限
- H1_BOUNCE_RANGE_PIPS: H1安値/高値からこのpips以内ならエントリーを見送る
- SCALP_MODE: スキャルプモードを強制したい場合に true/false を指定
- ADX_SCALP_MIN: スキャルプ実行に必要なADX下限
- SCALP_SUPPRESS_ADX_MAX: この値を超えるADXではSCALP_MODEをオフにする
- SCALP_TP_PIPS / SCALP_SL_PIPS: ボリバン幅を参照できないときのTP/SL
- SCALP_COND_TF: スキャルプ時に市場判定へ使う時間足 (デフォルト M1)
- TREND_COND_TF: トレンドフォロー時に市場判定へ使う時間足 (デフォルト M5)
- SCALP_OVERRIDE_RANGE: true でレンジ判定を無視してスキャルを実行

- SCALP_ENTER_SCORE / SCALP_HOLD_SCORE: スコアリングで `scalp_momentum` へ
  移行・維持する際のしきい値。推奨 `0.20` / `0.15`。
- RANGE_ADX_MIN: ADX がこの値を下回るとカウンターを加算し、連続
  `RANGE_ADX_COUNT` 回でスキャルプモードへ切替。推奨 `15`。
- QUICK_TP_MODE: true で2pips利確を高速に繰り返す専用モードを起動
- QUICK_TP_INTERVAL_SEC: Quick TP モードでのエントリー間隔秒数
- QUICK_TP_UNITS: Quick TP モードで使う発注ユニット数

### OANDA_MATCH_SEC

  ローカルトレードと OANDA 取引を照合するときの許容秒数。デフォルトは60秒。

## 追加環境変数

- USE_LOCAL_MODEL: OpenAI APIの代わりにローカルモデルを使用するか (true/false)
- LOCAL_MODEL_NAME: 使用するローカルモデル名 (例: distilgpt2)
- USE_LOCAL_PATTERN: チャートパターン検出をローカルで行うか (true/false)
- USE_CANDLE_SUMMARY: ローソク足情報を平均値で要約して AI へ渡すか (true/false)
- FRED_API_KEY: 米国経済指標取得に使用するFRED APIキー
- KAFKA_SERVERS: Kafkaブローカーの接続先リスト (例: localhost:9092)
  - KAFKA_BROKERS や KAFKA_BROKER_URL、KAFKA_BOOTSTRAP_SERVERS でも同じ値を指定可能
- METRICS_TOPIC: メトリクス送信用のKafkaトピック名
- MAX_CVAR: ポートフォリオ許容CVaR上限 (例: 5.0)
- LOSS_LIMIT: SafetyTriggerによる累積損失上限
- ERROR_LIMIT: 許容エラー回数の上限
- USE_OFFLINE_POLICY: オフライン学習ポリシーを利用するか (true/false)
- PATTERN_TFS: パターン検出を行う時間足一覧 (例: M5,M15)
## 認証情報

- **OPENAI_API_KEY**: OpenAI API のキー (デフォルト: なし)
- **OANDA_API_KEY**: OANDA のアクセスキー (デフォルト: なし)
- **OANDA_ACCOUNT_ID**: OANDA のアカウントID (デフォルト: なし)

## ネットワーク設定

- **OANDA_API_URL**: OANDA REST API のベースURL (デフォルト: https://api-fxtrade.oanda.com/v3)
- **OANDA_STREAM_URL**: OANDA ストリームAPIのURL (デフォルト: https://stream-fxtrade.oanda.com/v3)
- **HTTP_MAX_RETRIES**: HTTPリトライ回数 (デフォルト: 3)
- **HTTP_BACKOFF_CAP_SEC**: リトライ待ち時間上限秒 (デフォルト: 8)
- **HTTP_TIMEOUT_SEC**: HTTPリクエストのタイムアウト秒 (デフォルト: 10)

## サーバー設定

- **API_PORT**: FastAPI サーバーのポート (デフォルト: 8080)
- **METRICS_PORT**: Prometheus メトリクス用ポート (デフォルト: 8001)
- **LOG_LEVEL**: ログ出力レベル (デフォルト: INFO)
- **PAPER_MODE**: true で実取引せずシミュレーションを行う (デフォルト: false)

## リスク管理

- **ACCOUNT_BALANCE**: 口座残高想定値 (デフォルト: 10000)
- **RISK_PER_TRADE**: PortfolioRiskManager が参照する1トレードあたりのリスク割合 (デフォルト: 0.005)
- **ENTRY_RISK_PCT**: 1トレードあたりのリスク許容比率 (デフォルト: 0.01)
- **PIP_VALUE_JPY**: 1pipあたりの円換算値 (デフォルト: 100)
- **MARGIN_WARNING_THRESHOLD**: 証拠金アラートを出す残高比率 (デフォルト: 0)

## 多数決フロー関連

- **STRAT_TEMP**: Strategy Select で使う temperature。
- **STRAT_N**: Strategy Select が一度の API 呼び出しで生成する候補本数。
- **STRAT_VOTE_MIN**: 採用に必要な一致数。
- **ENTRY_BUFFER_K**: Entry Plan を平均化するバッファ長。
- **REGIME_ADX_TREND**: Regime 判定でトレンドとみなすADX値。
- **REGIME_BB_NARROW**: Range 判定で用いるBB幅の閾値。
フロー全体の解説は [majority_vote_flow.md](majority_vote_flow.md) を参照してください。

## AI 運用オプション

### ENTRY_USE_AI

エントリー判断でAIを使用するかどうか。`false` を指定すると `tech_arch` パイプラインが既定のATR倍率でTP/SLを計算します。

### MAX_AI_EXIT_CALLS

ポジション保有中にAIへエグジット判断を問い合わせる最大回数。デフォルトは5。

### USE_VOTE_PIPELINE

多数決アーキテクチャ(vote_arch)を利用するか。`false` なら `tech_arch` に切り替わります。

### USE_VOTE_ARCH

vote_arch 全体を無効化したい場合に `false` を指定します。

### FALLBACK_FORCE_ON_NO_SIDE

AI が `side:"no"` を返しても、現在のトレンド方向へエントリーを強制するかを決め
ます。デフォルトは `false` です。

### FORCE_ENTRY_AFTER_AI

AI 判断後にフィルタで拒否されても必ず注文を実行するかどうかを決めます。デフォルトは `true` です。

### ALWAYS_ENTRY

フィルタに阻まれても毎回エントリー処理を行うかどうか。デフォルトは `false` です。

### FALLBACK_DEFAULT_SL_PIPS

AI が SL 値を返さない場合に利用する予備の幅(pips)。デフォルトは `8` です。

### FALLBACK_DEFAULT_TP_PIPS

AI が TP 値を返さない場合に利用する予備の幅(pips)。デフォルトは `12` です。


### FALLBACK_DYNAMIC_RISK

`true` を指定すると、指標から自動算出した TP/SL を使用します。デフォルトは
`false` です。

設定例:

```
FALLBACK_FORCE_ON_NO_SIDE=true
FALLBACK_DEFAULT_SL_PIPS=10
FALLBACK_DEFAULT_TP_PIPS=15
FALLBACK_DYNAMIC_RISK=true
FORCE_ENTRY_AFTER_AI=true
ALWAYS_ENTRY=true
```

### Atmosphere module

- `ATMOS_EMA_WEIGHT`: EMA傾きの重み付け。デフォルトは `0.4`。
- `ATMOS_RSI_WEIGHT`: RSIバイアスの重み付け。デフォルトは `0.3`。
- `ATMOS_THRESHOLD`: Atmosphereスコアがこの値以上でエントリーを許可。デフォルト `0.5`。
