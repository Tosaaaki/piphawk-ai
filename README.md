# PiphawkGenie

PiphawkGenie is an automated trading system that uses the OANDA REST API for order management and integrates OpenAI models for market analysis. The project provides a REST API for monitoring and runtime configuration as well as a job runner that executes the trading logic at a fixed interval.

For details on the role of each file and directory, see [docs/file_roles.md](docs/file_roles.md).

## System Overview

PiphawkGenie consists of the following components:

- **Job Runner** – periodically fetches market data, calculates indicators and
  places orders based on AI analysis.
- **REST API** – exposes status endpoints and allows runtime configuration via
  FastAPI.
- **React Frontend** – optional dashboard located under `piphawk-ui/`.
- **SQLite Database** – stores trade history and parameter changes.

The backend resides in the `backend/` directory and is designed to run either
directly with Python or inside Docker containers. Configuration values are
loaded from environment variables and optional YAML files under `config/`.
Trading decisions are determined through a majority vote pipeline that filters
indicators, selects a strategy via OpenAI, and averages entry plans. For a
detailed diagram see [docs/majority_vote_flow.md](docs/majority_vote_flow.md).
An alternative fully technical pipeline is available under
`piphawk_ai.tech_arch`; see [docs/technical_pipeline.md](docs/technical_pipeline.md).
Set `USE_VOTE_PIPELINE=false` to force this technical pipeline.
Set `SCALP_MODE=true` to always load scalping parameters at startup.
With `ENTRY_USE_AI=false` the system skips LLM entry tuning and simply applies
fixed ATR multiples.
The module exposes `run_cycle()` which implements a simplified M5 entry flow.

## QuickStart

1. Clone the repository

   ```bash
   git clone https://github.com/yourname/piphawk-ai.git
   cd piphawk-ai
   ```

2. Create `.env` from the template

   ```bash
   cp .env.template .env
   ```
   Edit the file and set your API keys. Detailed options are covered in the
   [Setup](#setup) section.
3. Build and run the backend container

   ```bash
   DOCKER_BUILDKIT=1 docker build -t piphawk-ai .
   docker run --env-file .env -p 8080:8080 \
     -v $(pwd)/backend/logs:/app/backend/logs piphawk-ai
   ```

4. Start the React UI

   ```bash
   cd piphawk-ui
   npm install
   npm start
   ```

See [docs/quick_start_ja.md](docs/quick_start_ja.md) for the Japanese guide.
For detailed instructions, refer to [Setup](#setup).

## Features

### Implemented

- Automated entry and exit using OpenAI models with technical and macro context.
- Majority-vote pipeline with plan buffering or a simplified technical pipeline.
- StrategySelector employs LinUCB and optional offline policies for mode choice.
- Multi-timeframe indicators, regime detection and dynamic trailing-stop logic.
- Chart pattern detection via OpenAI or local scanner.
- Atmosphere module adjusts strategy weights using EMA slope and RSI bias.
- Tick-level micro scalp entries via `openai_micro_scalp.py`.
- CVaR-based portfolio risk management and dynamic lot sizing.
- Parameters loaded from environment variables or YAML files with hot reload.
- Trade, parameter and prompt history stored in SQLite.
- API provides runtime control, Prometheus metrics and LINE notifications.
- React dashboard for monitoring and configuration.
- Dockerfiles for containerized deployment.
- Offline analysis scripts for regime classification and clustering under
  `analysis/`.
- Reinforcement learning and feature generation utilities in
  `offline_training/`.
- Simple backtest helpers are available via `analysis/backtest_utils.py`.
- Quick TP mode for rapid 2-pip scalping via `execution/quick_tp_mode.py`.
- `jobs/pending_order_recheck.py` reevaluates pending limit orders.
- Lightweight metrics helpers in `fast_metrics.py` compute mid price and spread.
- Walk-forward optimization pipeline under `pipelines/walk_forward/` automates training and forward tests.
- Bayesian optimization of filter parameters with Optuna via `optuna/bayes_filter_opt.py`.
- Diagnostic utilities save prompts and metrics to SQLite using `diagnostics/diagnostics.py`.
- Monitoring modules such as `monitoring/gpt_usage.py` publish Prometheus metrics.
- `deploy.sh` automates repository updates and container rebuilds.

### Planned

- Further reinforcement learning tooling. See [docs/training_guide.md](docs/training_guide.md).
- Usage of the new atmosphere signal is documented in
  [docs/atmosphere_signal.md](docs/atmosphere_signal.md).

## Setup

See [AGENTS.md](AGENTS.md) for coding guidelines and test commands.

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourname/piphawk-ai.git
   cd piphawk-ai
   ```

2. **Install dependencies**
   It is recommended to use a virtual environment.

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --extra-index-url https://download.pytorch.org/whl/cpu -r backend/requirements.txt
   pip install -r requirements-dev.txt
   ```

   The indicator modules require **pandas**. If it is not installed, add it with:

   ```bash
   pip install pandas
   # optional linting
   pip install flake8
   ```

3. **Environment variables**
   まずルートの `.env.template` をコピーして `.env` を作成します。
   必要に応じて `backend/config/secret.env.example` の値も追記してください。

   ```bash
   cp .env.template .env
   cp backend/config/settings.env .
   # Edit `.env` and set OPENAI_API_KEY, OANDA_API_KEY and OANDA_ACCOUNT_ID
   ```

   アプリケーションが参照する環境変数の優先順位は
   **外部で設定された値 → `.env` → `backend/config/settings.env` → `backend/config/secret.env`**
   です。必要に応じて `settings.env` の値も調整してください。
詳細な変数解説は [docs/env_reference.md](docs/env_reference.md) を、
カテゴリ別の一覧は [docs/settings_categories.md](docs/settings_categories.md) を参照してください。

### マイクロスキャルプの有効化

`docs/aggressive_scalp.md` で解説されているマイクロスキャルプを利用すると、
Tick データから超短期エントリーを判断できます。`.env` に次の値を追加してください。

```bash
MICRO_SCALP_ENABLED=true
MICRO_SCALP_LOOKBACK=5
MICRO_SCALP_MIN_PIPS=1
```

`backend/strategy/openai_micro_scalp.py` が OpenAI API へ問い合わせ、
`enter: true` が返れば通常のスキャルプより優先して採用されます。
`enter: false` またはエラー時は `openai_scalp_analysis.py` へフォールバックします。

```text
Ticks → openai_micro_scalp.py → enter: true → submit order
                     ↓ false / error
                openai_scalp_analysis.py
```

設定変更後はコンテナを再起動して反映します。

### Atmosphere module

The Atmosphere module adjusts strategy weights based on EMA slope and RSI bias.
Add the following variables to `.env` and tune as needed.

```bash
ATMOS_EMA_WEIGHT=0.4
ATMOS_RSI_WEIGHT=0.3
ATMOS_THRESHOLD=0.5
```

See [docs/atmosphere_module.md](docs/atmosphere_module.md) for usage details.

### Directory Structure

```
piphawk-ai/
├── backend/       # FastAPI server, job runner and trading logic
├── piphawk-ui/    # React frontend (optional)
├── config/        # YAML configuration files and loaders
├── analysis/      # Analysis scripts and utilities
├── indicators/    # Technical indicator modules
└── tests/         # Unit tests
```

The root also includes `Dockerfile` definitions for containerized deployment and
`trades.db` as the default SQLite database path.
When running inside Docker this file is located at `/app/backend/logs/trades.db` by default.

For details on the role of each top-level file and directory, see
[docs/file_roles.md](docs/file_roles.md).

### Logging

Set the `LOG_LEVEL` environment variable to control verbosity. When `DEBUG` is
enabled, additional messages such as AI rejection reasons are written to the
console.

### Using strategy.yml

`config/strategy.yml` を作成すると、キーと値を YAML 形式で指定して環境変数を上書きできます。

```yaml
MIN_RRR: 1.5
ATR_RATIO: 1.8
```

`config.params_loader.load_params("config/strategy.yml")` を呼び出すと `.env` より後から読み込まれ、簡単にパラメータを切り替えられます。
設定変更後はジョブランナーを再起動するか、この関数を再度実行して環境変数を更新してください。

スキャルピング用の設定例は以下の通りです。

```yaml
ADX_SCALP_MIN: 35
SCALP_SUPPRESS_ADX_MAX: 60
SCALP_TP_PIPS: 8
SCALP_SL_PIPS: 8
SCALP_COND_TF: M1
TREND_COND_TF: M5
SCALP_OVERRIDE_RANGE: true
```

スキャルプとトレンドフォローを完全に分けたい場合は
`config/scalp_params.yml` と `config/trend.yml` を用意し、
`params_loader.load_params()` へ読み込ませます。
詳しくは `docs/scalp_vs_trend.md` を参照してください。
YAML ファイルの変更は `settings.env` と同様、ジョブランナー起動時に読み込まれ
ます。値を変えた後はジョブランナーを再起動するか、明示的に
`params_loader.load_params()` を実行してください。

### Using mode_detector.yml

`analysis/mode_detector.py` では ADX や ATR、EMA のしきい値を `config/mode_detector.yml` から読み込みます。環境変数 `MODE_DETECTOR_CONFIG` を指定すると別パスを参照できます。

```yaml
adx_trend_min: 25
adx_range_max: 18
atr_pct_min: 0.003
ema_slope_min: 0.1
```

`mode_detector.load_config()` を呼び出すと上記の辞書が返り、存在しない項目はデフォルト値が適用されます。

### LLM model settings

`strategy.yml` では利用する OpenAI モデルを個別に指定できます。現在はトレードモー
ド判定がローカルの `analysis.detect_mode_simple()` へ置き換わったため、`mode_selector`
キーは無視されます。以下の例ではエントリーとエグジットのみ AI モデルを指定してい
ます。

```yaml
LLM:
  entry_logic: gpt-4.1-nano
  exit_logic: gpt-4.1-nano
```

`AI_ENTRY_MODEL` や `AI_EXIT_MODEL` などの値は `.env` を編集して変更できます。

これらはそれぞれ `AI_ENTRY_MODEL`、`AI_EXIT_MODEL` 環境変数に展開されます。

ジョブランナーは ADX の値からスキャルプかトレンドフォローかを判断し、モードが
切り替わった際に `config/<mode>.yml` を自動で再読み込みします。環境変数
`AUTO_RESTART=true` を設定すると、読み込み後にプロセスを `os.execv()` で
再起動します。このとき `RESTART_MIN_INTERVAL` で最小再起動間隔を指定可能です。
`RESTART_STATE_PATH` でタイムスタンプを書き込むファイルを指定すると、連続再起動を
防ぎます。

### Switching OANDA accounts

別アカウントを利用する場合は、そのアカウント用のAPIトークンを発行し、`.env` の
`OANDA_API_KEY` と `OANDA_ACCOUNT_ID` を更新してください。また口座ごとにデータベ
ースを分けると管理が容易なため、`TRADES_DB_PATH` で別ファイルを指定することを推
奨します。

```bash
OANDA_API_KEY=<token for account 002>
OANDA_ACCOUNT_ID=001-009-13679149-002
TRADES_DB_PATH=trades-002.db
```

アカウントを切り替えたら一度 `init_db()` を実行し、その後
`backend.logs.update_oanda_trades` を走らせると最新履歴が保存されます。
ローカルの `trades` テーブルと OANDA の取引履歴を突き合わせて
実現損益を反映させるには `backend.logs.reconcile_trades` を実行します。
履歴更新から反映までを一度に行う場合は
`execution.sync_manager.sync_exits()` を呼び出してください。
分割エントリーに関する解説は `docs/scale_entry.md` にまとめています。
エントリーフィルタの詳細は `docs/entry_filter.md` を参照してください。
高位足の使い方に関する補足は `docs/higher_tf_strategy.md` を参照してください。
低ボラ時のエントリー仕様は `docs/low_vol_entry.md` を参照してください。
より積極的にスキャルプするための設定例は `docs/aggressive_scalp.md` にまとめています。
   `RANGE_CENTER_BLOCK_PCT` controls how close to the Bollinger band center price
    can be when ADX is below `ADX_RANGE_THRESHOLD`. Set to `0.3` (30%) to block
    entries near the middle of a range, helping suppress counter-trend trades.
   `BAND_WIDTH_THRESH_PIPS` defines the Bollinger band width that triggers
   range mode regardless of ADX. When the width falls below this value the system
   treats the market as ranging and the AI prompt notes that *BB width is
   contracting*.
`ENABLE_RANGE_ENTRY` を `true` にすると、ADX のノートレード判定を無視してレンジ相場でもエントリーを許可します。価格がボリンジャーバンド中心から `RANGE_ENTRY_OFFSET_PIPS` pips 以内にある場合は、市場注文をバンド端の LIMIT に変換します。この処理は `backend/strategy/entry_logic.py` で行われます。
`RANGE_ENTRY_NOTE` を指定すると、その内容が AI プロンプトに追記され、レンジ相場での細かな指示を外部から設定できます。
`USE_CANDLE_SUMMARY` を `true` にすると、ローソク足リストの代わりに平均値まとめを AI へ送信し、トークン消費を抑えられます。
`AI_PROFIT_TRIGGER_RATIO` defines what portion of the take-profit target must
be reached before an AI exit check occurs. The default value is `0.5` (50%).
`MAX_AI_EXIT_CALLS` limits how many times `propose_exit_adjustment()` runs per
position. Each call uses about 150 tokens so two calls cost roughly $0.001.
`SCALE_LOT_SIZE` sets how many lots are added when the AI exit decision is `SCALE`.
`MIN_SL_PIPS` enforces a minimum stop-loss size. If the AI suggests a smaller value the system uses this floor instead (default `8`). OpenAI プラン生成時にもこの値を下回らないよう補正し、ATR と直近スイング幅から算出される動的下限も適用される。またスキャルピングモードでもこの下限が尊重されるようになった。
`MIN_NET_TP_PIPS` sets the minimum take-profit after subtracting spread. Lower this value (for example `0.5`) when logs show `NET_TP_TOO_SMALL`.
`SL_COOLDOWN_SEC` is the waiting period after a stop-loss exit before another entry in the same direction is allowed. Default is `300` seconds.
`AI_COOLDOWN_SEC_OPEN` sets the minimum interval in seconds between AI calls while a position is open.
`AI_COOLDOWN_SEC_FLAT` defines the cooldown when no position is held.
`AI_REGIME_COOLDOWN_SEC` controls how often the AI checks market regime. Default is `15` seconds.
`AI_COOLDOWN_HIGH_VOL_MULT` shortens the cooldown during high-volatility sessions. A value of `0.5` halves the wait time.
`MIN_RRR` sets the minimum reward-to-risk ratio allowed when selecting a
take-profit. The TP level is now chosen to maximise expected value while
keeping the ratio at or above this threshold.
`ENFORCE_RRR` forces the TP/SL combination to respect this ratio. When set to
`true` the entry logic adjusts the take-profit so that `tp_pips / sl_pips`
meets `MIN_RRR` and logs the final values at INFO level.
Recommended values are `MIN_RRR=1.2` with `ENFORCE_RRR=true` for conservative
trading.
`ATR_RATIO` は ATR の短期平均を長期平均で割った値がこのしきい値を超えるとリスク過熱とみなし、エントリーを控えます。
`STAGNANT_EXIT_SEC` sets how long a profitable position can stagnate before the
system asks the AI to close it. If `STAGNANT_ATR_PIPS` is greater than zero and
ATR falls below this value, the position is considered stagnant once the time
threshold passes.
`MIN_HOLD_SECONDS` defines the minimum hold duration before any exit logic runs.
`REVERSAL_EXIT_ATR_MULT` and `REVERSAL_EXIT_ADX_MIN` define how far beyond the
opposite Bollinger Band the close must be, and the minimum ADX, before a reversal
exit is considered.
`POLARITY_EXIT_THRESHOLD` sets the absolute polarity required to trigger a polarity-based early exit. The default is `0.4`.
`HIGH_ATR_PIPS` defines the ATR level in pips considered "high". When this is met and `ADX` falls below `LOW_ADX_THRESH`, the system exits early.
`LOW_ADX_THRESH` is the ADX threshold paired with `HIGH_ATR_PIPS` for this early-exit rule.
`MM_DRAW_MAX_ATR_RATIO` controls how much drawdown from the peak is allowed before the peak exit guard triggers. The value is multiplied by ATR to derive the threshold.
`PULLBACK_LIMIT_OFFSET_PIPS` is the base distance for a pullback LIMIT order when the AI proposes a market entry. The actual offset is derived from ATR and ADX, and if price runs away while the trend persists the order can be switched to a market order under AI control.
`AI_LIMIT_CONVERT_MODEL` sets the OpenAI model used when asking whether a pending LIMIT should be switched to a market order. The default is `gpt-4.1-nano`.
`PULLBACK_PIPS` defines the base pullback distance used when placing limit orders. The defaults are `2` and `3` respectively.
`PULLBACK_ATR_RATIO` は ATR に基づくプルバック深度の調整係数で、1.0 なら ATR と同じ値、0.5 なら半分の深さを待ちます。
`PIP_SIZE` specifies the pip value for the traded pair (e.g. `0.01` for JPY pairs) and is used when calculating the new volatility‑based pullback threshold.
`TRADE_TIMEFRAMES` allows overriding which candle intervals are fetched for analysis. Specify as `S10:60,M1:20,M5:50,M15:50,H1:120,H4:90,D:90` to cover short to long horizons. `S10` denotes 10‑second candles.
The system derives a dynamic pullback requirement from ATR, ADX and recent price swings. If indicators are missing, the fallback is `PULLBACK_PIPS`.
`BYPASS_PULLBACK_ADX_MIN` を設定すると、その値以上の ADX ではプルバック待機を完全にスキップし、AI プロンプトにも "Pullback not required" と記載されます。
`ALLOW_NO_PULLBACK_WHEN_ADX` を `20` に設定すると、ADX が 20 以上のときプルバック不要と明示的に AI に伝えます。
`TP_BB_RATIO` scales the Bollinger band width when deriving a fallback take-profit target. For example, `0.6` uses 60% of the band width.
`RANGE_ENTRY_OFFSET_PIPS` determines how far from the Bollinger band center price must be (in pips) before converting a market order to a LIMIT when `ENABLE_RANGE_ENTRY` is active. If the price is within this range, `entry_logic.py` places the order near the band high or low. The default is `3`.
`想定ノイズ` is automatically computed from ATR and Bollinger Band width and included in the AI prompt to help choose wider stop-loss levels.
The indicators module also calculates `adx_bb_score`, a composite value derived from ADX changes and Bollinger Band width. This score is passed to the AI so it can gauge momentum strength from multiple angles.
`NOISE_SL_MULT` は AI が算出した SL をこの倍率で拡大します (default `1.5`).
`TP_ONLY_NOISE_MULT` を設定すると、SL が想定ノイズ × この倍率未満の場合 TP のみを設定します。
`BE_VOL_ADX_MIN` と `BE_VOL_SL_MULT` を設定すると、ブレイクイーブン発動時に ADX
がこの値以上なら SL を `entry_price ± ATR × BE_VOL_SL_MULT` に調整します。
`PATTERN_NAMES` lists chart pattern names passed to the AI or local scanner for detection, e.g. `double_bottom,double_top,doji`.
`LOCAL_WEIGHT_THRESHOLD` は 0〜1 の値で、ローカル判定と AI 判定の整合度スコアがこの値以上ならローカルを、未満なら AI を優先します。`USE_LOCAL_PATTERN` を `true` にすると常にローカル検出のみを使用し、`settings.env` のデフォルト値も `true` です。
`PATTERN_MIN_BARS` でパターン完成に必要なローソク足の本数を、`PATTERN_TOLERANCE` で高値・安値の許容誤差を調整できます。
`PATTERN_EXCLUDE_TFS` に `M1` などを指定すると、その時間足ではパターン検出を行いません。
`PATTERN_TFS` を `M1,M5` のように設定すると、指定した時間足のみをスキャンします。
`STRICT_ENTRY_FILTER` controls whether the M1 RSI cross signal is required. Set to `false` to skip the cross check (default `true`).
`SCALP_STRICT_FILTER` applies the same rule only in scalp mode. Set to `true` when an M1 RSI cross must be observed for scalping entries.
`HIGHER_TF_ENABLED` を `true` にすると、上位足ピボットとの距離も TP 計算に利用します。
`VOL_MA_PERIOD` sets the averaging window for volume checks. If the average falls below `MIN_VOL_MA` (or `MIN_VOL_M1`) the entry is blocked.
`ADX_SLOPE_LOOKBACK` defines how many candles to look back when computing ADX slope, and `ADX_DYNAMIC_COEFF` scales the ADX threshold based on Bollinger width.
`EMA_FLAT_PIPS` determines the range treated as a flat EMA slope; convergence with a reversal within this range triggers the *急反転* filter.
`OVERSHOOT_ATR_MULT` blocks entries when price overshoots below the lower Bollinger Band by this multiple of ATR. `OVERSHOOT_DYNAMIC_COEFF` adjusts this multiplier based on Bollinger width.
`OVERSHOOT_BASE_MULT` defines the ATR multiple right after an overshoot is detected, gradually relaxing up to `OVERSHOOT_MAX_MULT` by `OVERSHOOT_RECOVERY_RATE` per minute.
`OVERSHOOT_MAX_PIPS` sets the maximum overshoot allowed in pips.
`OVERSHOOT_DYNAMIC` enables ATR-based scaling of this limit (`OVERSHOOT_FACTOR` with floor/ceil).
`OVERSHOOT_MODE` set to `warn` logs a warning instead of blocking.
`OVERSHOOT_WINDOW_CANDLES` defines how many recent candles to inspect when evaluating overshoot range.
`OVERSHOOT_WINDOW_CANDLES` defines how many recent candles are averaged when computing the overshoot. Example: setting `OVERSHOOT_WINDOW_CANDLES=3` bases the filter on the last three closes.
`REV_BLOCK_BARS`, `TAIL_RATIO_BLOCK` and `VOL_SPIKE_PERIOD` configure the Recent Candle Bias filter, blocking entries when recent candles show sharp tails or volume spikes in the opposite direction.
`STRICT_TF_ALIGN` enforces multi-timeframe EMA alignment before entering.
`COUNTER_TREND_TP_RATIO` scales down the take-profit when entering against the higher timeframe trend.
`BLOCK_COUNTER_TREND` (default `true`) skips entries when both M15 and H1 EMA direction oppose the trade.
`COUNTER_BYPASS_ADX` lets counter entries through when the latest M5 ADX is high (e.g. 30+) and matches the entry side.
`COUNTER_RANGE_ADX_MAX` disables the counter-trend block when the M5 ADX is below this value, allowing range trades.

`TF_EMA_WEIGHTS` specifies the weight of each timeframe when evaluating EMA alignment, e.g. `M5:0.4,H1:0.3,H4:0.3`.
`AI_ALIGN_WEIGHT` adds the AI's suggested direction to the multi-timeframe alignment check.
`ALIGN_BYPASS_ADX` bypasses the alignment logic and returns the AI side when the latest M5 ADX meets or exceeds this value.
`LT_TF_PRIORITY_ADX` defines the ADX level on the lower timeframe that triggers temporary down‑weighting of higher timeframes when an EMA cross occurs.
`LT_TF_WEIGHT_FACTOR` is the factor applied to higher timeframe weights during that period.

`ALLOW_DELAYED_ENTRY` (default `true`) lets the AI return `"mode":"wait"` when a trend is overextended. The job runner will keep polling and enter once the pullback depth is satisfied.

`OANDA_MATCH_SEC` はローカルトレードと OANDA 取引を照合するときの許容秒数です。デフォルトは `60` です。

`config/strategy.yml` にはリスク管理とフィルタ、再エントリー条件をまとめています。初期値は以下の通りです。

```yaml
risk:
  min_atr_sl_multiplier: 1.2
  min_rr_ratio: 1.2
filters:
  avoid_false_break:
    lookback_candles: 20
    threshold_ratio: 0.2
reentry:
  enable: true
  trigger_pips_over_break: 1.5
```

`min_atr_sl_multiplier` は ATR を基にした最小ストップ幅の倍率、`min_rr_ratio` は最低リスクリワード比を示します。`avoid_false_break` ではブレイク失敗回避のための期間と閾値を設定し、`reentry` を有効にするとブレイク後に再びエントリーする条件を制御できます。
これらの値は `params_loader.load_params()` により `MIN_ATR_MULT` などの環境変数に変換されます。

#### fallback ブロック

`config/strategy.yml` ではエントリー判定に失敗した際の予備動作も定義できます。

```yaml
fallback:
  force_on_no_side: false
  default_sl_pips: 12
  default_tp_pips: 18
  dynamic_risk: false
```

`force_on_no_side` は AI が `side: "no"` を返してもトレンド方向のエントリーを強制するかどうかを決めます。`default_sl_pips` と `default_tp_pips` は AI から値が得られない場合の初期値で、`dynamic_risk` を `true` にすると指標から SL/TP を自動計算します。これらは `FALLBACK_FORCE_ON_NO_SIDE`, `FALLBACK_DEFAULT_SL_PIPS`, `FALLBACK_DEFAULT_TP_PIPS`, `FALLBACK_DYNAMIC_RISK` 環境変数として読み込まれます。

## パラメータ変更履歴の確認

`init_db()` でデータベースを作成または更新した後、`log_param_change()` と `log_trade()` を
使って変更内容と取引を記録できます。記録された履歴は `analyze_param_performance()` で集計
できます。

```bash
python3 - <<'EOF'
from backend.logs.log_manager import init_db, log_param_change, log_trade
from backend.analysis.param_performance import analyze_param_performance

init_db()
log_param_change("EMA_PERIOD", 50, 55, ai_reason="tuning")
log_trade(
    instrument="USD_JPY",
    entry_time="2024-01-01T00:00:00Z",
    entry_price=140.0,
    units=1000,
    ai_reason="example",
    exit_time="2024-01-01T01:00:00Z",
    exit_price=140.5,
    profit_loss=50,
)

result = analyze_param_performance()
print(result)
EOF
```

出力は次のようなリスト形式になります。

```text
[{'timestamp': '...', 'params': {...}, 'metrics': {...}}, ...]
```

## Running the API

The API exposes endpoints for status checks, a simple dashboard and runtime settings. Start it from the packaged module:

```bash
python -m piphawk_ai.main api
```

## LINE 通知設定

API から LINE にメッセージを送信するには、まず `.env` に以下の環境変数を設定します。

```bash
LINE_CHANNEL_TOKEN=<your_line_token>
LINE_USER_ID=<your_line_user_id>
```

次のコマンドで API を起動してください。

```bash
python -m piphawk_ai.main api
```

テスト用エンドポイント `/notifications/send` を利用すると送信確認ができます。

```bash
curl -X POST http://localhost:8080/notifications/send
```

設定画面や `/notifications/settings` からトークンとユーザー ID を更新すると
環境変数にも反映され、即座に送信処理に利用されます。

## Running the Job Scheduler

The job runner performs market data collection, indicator calculation and trading decisions. Start it via the packaged module:

```bash
python -m piphawk_ai.main job
```

If the optional performance logger was added earlier, each job loop's timing
will be appended to `backend/logs/perf_stats.jsonl`.

Both the API and the job runner can run from the same Docker image.
For an API-only container, tag the build separately and override the command with
`python -m piphawk_ai.main api`.

## Metrics Monitoring

The API exposes Prometheus metrics at `/metrics`. The job runner also starts a
Prometheus server so monitoring tools can scrape data. Set `METRICS_PORT` to
control the port (default `8001`).

### Apple Silicon (ARM) users

If you are on an M1/M2 Mac or other ARM-based machine, build the images for
the `linux/amd64` platform so they run correctly:

```bash
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -f Dockerfile .
```

The Dockerfile copies the `config` directory so YAML files like `strategy.yml`
are bundled into the image. When you start the job runner container, these
parameters are loaded automatically.

Use the same flag if building separate images for the API and job runner.
The default tag launches the job scheduler. Create an API image with a custom
tag and command override:

```bash
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -t piphawk-ai:api .
docker run --rm piphawk-ai:api python -m piphawk_ai.main api
```

Running x86 containers under emulation can be slower and some dependencies may not behave exactly the same
as on native x86 hardware.

## Database

Trade history is stored in `trades.db` (SQLite) at the repository root by default.
You can override the path with the environment variable `TRADES_DB_PATH`.
When running inside Docker this defaults to `/app/backend/logs/trades.db`.

SQLite uses WAL (Write-Ahead Logging) mode. For existing databases run:

```bash
sqlite3 trades.db "PRAGMA journal_mode=WAL;"
```

The table now includes an `ai_response` column which stores the full text returned
by the AI when opening or closing a trade. In addition `score_version` records
the scoring algorithm version used for that trade. Run `init_db()` once to add
the column to older databases.

`prompt_logs` テーブルも追加され、送信したプロンプトとモデルからの応答が保存されます。
この履歴は将来の強化学習や戦略分析に利用できます。`init_db()` を実行すると自動
作成されます。

If you need a clean database locally, copy the example file if available:

```bash
cp backend/logs/trades.db trades.db
```

or create a fresh one using the helper in `backend.logs.log_manager`:

```bash
python3 - <<'EOF'
from backend.logs.log_manager import init_db

init_db()
EOF
```

This helper also upgrades older databases to include new columns and tables (e.g. `errors`) and ensures WAL mode is enabled. See `docs/db_migration.md` for details.
If you upgrade from a version before the `account_id` column was added to `oanda_trades`, running `init_db()` once will create it automatically.

To inspect parameter adjustments logged by the strategy analyzer, run
`backend/logs/show_param_history.py`. Filter by parameter name or period:

```bash
python3 backend/logs/show_param_history.py --param RSI_PERIOD --days 7
```

データベースのテーブル構成を確認するには次のスクリプトを実行します。

```bash
python3 -m backend.logs.show_tables
```

### Database cleanup

The database and `exit_log.jsonl` can grow large over time. Run the cleanup script to shrink the database and remove old log entries:

```bash
python3 -m backend.logs.cleanup
```

Set the `DAYS` environment variable to keep more history:

```bash
DAYS=60 python3 -m backend.logs.cleanup
```

### Filter statistics

`analysis/filter_statistics.py` を使うと、エントリーを阻止したフィルター理由の集計
結果を表示できます。`TRADES_DB_PATH` が未指定の場合は `trades.db` を参照します。

```bash
python3 -m analysis.filter_statistics
```

### System cleanup

Old cache files and log archives can consume disk space over time. Run the
helper script below or enable the provided systemd timer for periodic cleanup.
When ``sudo`` is not available, the script automatically runs the commands
without it:

```bash
python3 maintenance/system_cleanup.py
```
実行時には確認プロンプトが表示されます。`--yes` を付けると確認なしで実行でき、
`--dry-run` を指定するとコマンドを表示するだけで実行しません。

To set up the systemd timer automatically, run the helper script below
(requires `systemctl`):

```bash
bash maintenance/install_cleanup_service.sh
```

This copies `maintenance/system_cleanup.service` and
`maintenance/system_cleanup.timer` to `/etc/systemd/system/` and enables the
timer so cleanup runs weekly.

### Disk guard

`maintenance/disk_guard.py` checks the root filesystem usage and triggers
`system_cleanup.py` automatically when the usage reaches the threshold.
Set the `CLEANUP_THRESHOLD` environment variable to adjust it (default 80%).
Invoke it in
the main loop or run it manually:

```bash
python3 maintenance/disk_guard.py
```

`docker_cleanup.sh` も用意しており、ジョブランナーや cron から直接呼び出せます。しきい値は環境変数 `THRESHOLD` で調整可能です。

```bash
THRESHOLD=80 bash maintenance/docker_cleanup.sh
```

### Kafka log retention

`docker-compose.yml` sets Kafka's `log.retention.hours` and
`log.retention.bytes` via environment variables so old log segments are removed
automatically. By default, logs older than seven days or exceeding **10 GiB**
are pruned without manual intervention.


The Kafka container includes a simple health check. `piphawk` waits for this
check to succeed by using `depends_on` with `condition: service_healthy`.
### Kafka healthcheck

`docker-compose.yml` includes a healthcheck so the `piphawk` container waits for
Kafka to become ready before connecting. This avoids `ECONNREFUSED` errors
during startup races.

コンテナが137エラーで終了する場合はメモリ不足の可能性があります。`docker-compose.yml`の`mem_limit`を増やしてメモリ割当を見直してください。

## React UI

The active React application lives in `piphawk-ui/` and was bootstrapped with Create React App. Run it locally with:

```bash
cd piphawk-ui
npm install
npm start
```

Create `.env.development` with the backend URL before running `npm start`:

```bash
echo "REACT_APP_API_URL=http://localhost:8080" > .env.development
```

Node.js **14 or later** is required (Node 18 LTS recommended). The React UI is
built with **React 18** and should be run with that major version.

## Building the Frontend

To create a production build of the React UI, use `npm run build` inside
`piphawk-ui/`. You can optionally set `REACT_APP_API_URL` to target a different
backend during the build:

```bash
REACT_APP_API_URL=https://<api-host> npm run build
```

If `REACT_APP_API_URL` is omitted, the application defaults to
`http://localhost:8080`.

## License

This project is provided as-is under the MIT license.

## Disclaimer

Past performance does not guarantee future results. Use this project at your own risk.

## Market Data Utilities

Market data helpers are available under `backend/market_data/`.
`fetch_tick_data` retrieves the latest pricing snapshot for a specified
instrument.

```python
from backend.market_data.tick_fetcher import fetch_tick_data

tick = fetch_tick_data("USD_JPY")
```

## Price Formatting Utilities

Order prices must have the correct number of decimal places or OANDA will reject
the request.  The helpers under `backend.utils.price` round values to the
allowed precision and return them as strings.  `format_price()` performs this
lookup for you and preserves trailing zeros.

```python
from backend.utils.price import format_price

price_str = format_price("USD_JPY", 143.25099999999998)
print(price_str)  # "143.251"
```

JPY pairs use three decimal places while most other instruments use five.
Extend the module's map if additional pairs are needed.

## Frontend Components

Example React components are provided under `docs/examples/` and are styled with `styled-components` for a dark dashboard UI:

- `Dashboard.jsx` – trade history table, performance summary, and a line chart placeholder.
- `Settings.jsx` – controls for numeric and boolean parameters with sliders and toggles.
- `ContainerControls.jsx` – start/stop/restart buttons with spinner indicators.
- `LogViewer.jsx` – tabbed viewer showing errors and recent trades.

These components are examples only and are not yet integrated into a build setup.

## AIによるチャートパターン判定

`backend/strategy/pattern_ai_detection.py` に `detect_chart_pattern` 関数が追加されました。ローソク足データと判定したいパターン名のリストを渡すと、OpenAI が該当パターンの有無を返します。

```python
from backend.strategy.pattern_ai_detection import detect_chart_pattern

candles = [
    {"o": 1.0, "h": 1.2, "l": 0.9, "c": 1.1},
    {"o": 1.1, "h": 1.3, "l": 1.0, "c": 1.2},
]
result = detect_chart_pattern(candles, ["double_bottom", "head_and_shoulders"])
print(result)
```

返り値は `{"pattern": "<一致したパターン名>"}` もしくは `{"pattern": None}` の形式です。

`LOCAL_WEIGHT_THRESHOLD` を調整することで、AI 判定とローカル判定のどちらを優先するかを決められます。ローカルの結果だけを使いたい場合は `1.0` に設定してください。`USE_LOCAL_PATTERN` を使えば AI を経由せずローカル検出のみを行うこともできます。
ローカル判定を直接呼び出すには `pattern_scanner.scan()` を利用します。

対応パターン例:

- `double_bottom`
- `double_top`
- `head_and_shoulders`
- `doji`
- `hammer`
- `bullish_engulfing`
- `bearish_engulfing`
- `morning_star`
- `evening_star`
- `DoubleBottomSignal` class allows local detection of double-bottom patterns
- `DoubleTopSignal` class allows local detection of double-top patterns

複数時間足を使う場合は `get_trade_plan` の `pattern_tf` 引数で判定に利用する足を指定します。

```python
from backend.strategy.openai_analysis import get_trade_plan

candles_dict = {
    "M5": [...],   # 5分足
    "M15": [...],  # 15分足
}
plan = get_trade_plan({}, {}, candles_dict,
                      patterns=["double_bottom", "double_top"],
                      pattern_tf="M15")
```

## レジーム衝突処理
以前は `LOCAL_WEIGHT_THRESHOLD` を用いてローカル判定と LLM 判定の整合度を比較していましたが、現在は `analysis.detect_mode_simple()` のみを利用するためこの設定は不要になりました。`LOCAL_WEIGHT_THRESHOLD` はチャートパターン検出の重み付けにのみ使用されます。

## ブレイクアウト追随エントリー

`follow_breakout()` 関数はレンジをブレイクした直後の押し戻しが十分小さいかどうかを判定します。ADX が設定値以上であることを確認し、ブレイクアウト足と直近足の終値差を ATR と比較します。押し戻し幅が `FOLLOW_PULLBACK_ATR_RATIO` × ATR 以下であれば `True` を返します。

詳しいロジックは `docs/momentum_follow.md` を参照してください。

## 分割エントリー (Scaling)

The job runner can add to an existing position when the AI exit evaluator
returns `SCALE`. Set `SCALE_LOT_SIZE` in `settings.env` to control the lot
size of each additional entry (default `0.5`).

## Trailing Stop Updates

The trailing stop distance is recalculated on every loop when a position is in
profit. The job runner calls `order_manager.place_trailing_stop()` to update the
stop on the first trade ID, which replaces the previous order. OANDA cancels the
old trailing stop automatically once the new one is applied. See
`backend/strategy/exit_logic.py` lines 510-525 for the exact logic.
Mode-specific parameters can be set in `config/scalp_params.yml` and `config/trend.yml`.
For example, trend mode may use a wider trailing stop:

```yaml
TRAIL_TRIGGER_PIPS: 20
TRAIL_DISTANCE_PIPS: 10
```

## calc_min_sl による動的SL計算

`calc_min_sl()` を使うと ATR と直近スイング幅から最小ストップ値を算出できます。
ATR 倍率は `MIN_ATR_MULT` 環境変数、もしくは `config/strategy.yml` の
`risk.min_atr_sl_multiplier` で調整します。

```python
from backend.risk_manager import calc_min_sl

# 例: ATR=10pips、スイング差=8pips の場合
sl = calc_min_sl(10, 8, atr_mult=1.2, swing_buffer_pips=5)
print(sl)  # 13
```

計算された値を基準に TP/SL 候補を評価し、期待値が最大となる組み合わせを採用します。
`MIN_RRR` と `ENFORCE_RRR` を設定するとリスクリワード比を強制できます。
候補は `TP_CANDIDATES` / `SL_CANDIDATES` 環境変数や `strategy.yml` に記述可能です。

```yaml
risk:
  min_atr_sl_multiplier: 1.3
  min_rr_ratio: 1.2
TP_CANDIDATES: [10, 15, 20]
SL_CANDIDATES: [8, 10, 12]
```

## 4 レイヤー・スコアリングと TP/SL 最適化

エントリーロジックではトレンド、モメンタム、ボラティリティ、パターンの4要素を組み合わせたスコアリング方式を採用しています。重みは `SCORE_WEIGHTS` で調整でき、総合スコアが `ENTRY_SCORE_MIN` を上回った場合のみポジションを開きます。

TP/SL の組み合わせは複数候補から期待値を計算し、最も利益が見込めるものを自動選択します。`MIN_RRR` と `ENFORCE_RRR` を有効にするとリスクリワード比を維持したまま最適化されます。詳細は `docs/four_layer_scoring.md` を参照してください。

## Running Tests

Use the helper script to run unit tests:

```bash
./run_tests.sh
```

For lint and type checks, refer to the commands listed in
[AGENTS.md](AGENTS.md).

Some tests require optional dependencies such as `httpx` and `apscheduler`.
These tests call `pytest.importorskip()` to skip when the packages are missing.
Install all test requirements to ensure they run:

```bash
pip install -r requirements-test.txt
```

## プロンプト変更手順

各 AI 機能の指示文は `prompts/` ディレクトリにテンプレートとして保存されています。
モデルへ送る内容を調整したい場合は、対応するテンプレートファイルを編集するだけで
反映されます。コードを変更せずに `trade_plan.txt` や `scalp_analysis.txt`、
`trade_plan_instruction.txt` を更新することで、プロンプトを簡単にカスタマイズ
できます。
`PROMPT_TAIL_LEN` と `PROMPT_CANDLE_LEN` を設定すると、指標やローソク足の履歴本数
を変更できます。

## Signal Error Handling

Some signal functions return ``None`` on invalid input while others propagate
exceptions directly.  Use ``make_signal`` or ``recheck`` with caution and
validate input data beforehand.
