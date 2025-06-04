# Piphawk AI

Piphawk AI is an automated trading system that uses the OANDA REST API for order management and integrates OpenAI models for market analysis. The project provides a REST API for monitoring and runtime configuration as well as a job runner that executes the trading logic at a fixed interval.

## Setup

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
   pip install -r backend/requirements.txt
   ```
   The indicator modules require **pandas**. If it is not installed, add it with:
   ```bash
   pip install pandas
   ```
3. **Environment variables**
   まず `backend/config/secret.env.example` をコピーして `.env` を作成するか、
   自分で `.env` を新規作成してください。
   ```bash
   cp backend/config/secret.env.example .env
   cp backend/config/settings.env .
   # Edit .env and set OPENAI_API_KEY, OANDA_API_KEY and OANDA_ACCOUNT_ID
   ```
   アプリケーションは `.env`, `backend/config/settings.env`, `backend/config/secret.env` の順で環境変数を読み込みます。
   必要に応じて `settings.env` の値も調整してください。
詳しい環境変数一覧と設定例は `backend/config/ENV_README.txt` を参照してください。
`REV_BLOCK_BARS` は直近のローソク足から何本を逆行判定に使うか、
`TAIL_RATIO_BLOCK` はヒゲと実体の比がこの値を超えるとエントリーをブロックし、
`VOL_SPIKE_PERIOD` は出来高急増を検出する際の平均期間を指定します。

#### settings.env の主な変数
`backend/config/settings.env` には取引ロジックに関わる初期値がまとめられています。 `.env` の次に読み込まれるため、ここを編集すると大半の設定を簡単に変更できます。

- `DEFAULT_PAIR` … 取引する通貨ペア
- `MIN_RRR` … 最低リスクリワード比。`ENFORCE_RRR` と併用すると常にこの比率を保ちます
- `SCALE_LOT_SIZE` … 追加エントリー時のロット数
- `AI_MODEL` … OpenAI モデル名
- `LINE_CHANNEL_TOKEN` / `LINE_USER_ID` … LINE 通知に使用する認証情報

その他の変数は `backend/config/ENV_README.txt` を参照してください。
### Using strategy.yml
`config/strategy.yml` を作成すると、キーと値を YAML 形式で指定して環境変数を上書きできます。
```yaml
MIN_RRR: 1.5
ATR_RATIO: 1.8
```
`config.params_loader.load_params("config/strategy.yml")` を呼び出すと `.env` より後から読み込まれ、簡単にパラメータを切り替えられます。


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
分割エントリーに関する解説は `docs/scale_entry.md` にまとめています。
エントリーフィルタの詳細は `docs/entry_filter.md` を参照してください。
   `RANGE_CENTER_BLOCK_PCT` controls how close to the Bollinger band center price
   can be when ADX is below `ADX_RANGE_THRESHOLD`. Set to `0.3` (30%) to block
   entries near the middle of a range, helping suppress counter-trend trades.
   `BAND_WIDTH_THRESH_PIPS` defines the Bollinger band width that triggers
   range mode regardless of ADX. When the width falls below this value the system
   treats the market as ranging and the AI prompt notes that *BB width is
   contracting*.
`AI_PROFIT_TRIGGER_RATIO` defines what portion of the take-profit target must
be reached before an AI exit check occurs. The default value is `0.5` (50%).
`SCALE_LOT_SIZE` sets how many lots are added when the AI exit decision is `SCALE`.
`MIN_SL_PIPS` enforces a minimum stop-loss size. If the AI suggests a smaller value the system uses this floor instead (default `8`).
`SL_COOLDOWN_SEC` is the waiting period after a stop-loss exit before another entry in the same direction is allowed. Default is `300` seconds.
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
`MIN_HOLD_SEC` defines the minimum hold duration before any exit logic runs.
`REVERSAL_EXIT_ATR_MULT` and `REVERSAL_EXIT_ADX_MIN` define how far beyond the
opposite Bollinger Band the close must be, and the minimum ADX, before a reversal
exit is considered.
`POLARITY_EXIT_THRESHOLD` sets the absolute polarity required to trigger a polarity-based early exit. The default is `0.4`.
`PULLBACK_LIMIT_OFFSET_PIPS` is the base distance for a pullback LIMIT order when the AI proposes a market entry. The actual offset is derived from ATR and ADX, and if price runs away while the trend persists the order can be switched to a market order under AI control.
`AI_LIMIT_CONVERT_MODEL` sets the OpenAI model used when asking whether a pending LIMIT should be switched to a market order. The default is `gpt-4.1-nano`.
`PULLBACK_PIPS` defines the offset used specifically when the price is within the pivot suppression range. The defaults are `2` and `3` respectively.
`PIP_SIZE` specifies the pip value for the traded pair (e.g. `0.01` for JPY pairs) and is used when calculating the new volatility‑based pullback threshold.
`TRADE_TIMEFRAMES` allows overriding which candle intervals are fetched for analysis. Specify as `M1:20,M5:50,M15:50,H1:120,H4:90,D:90` to cover short to long horizons.
The system derives a dynamic pullback requirement from ATR, ADX and recent price swings. If indicators are missing, the fallback is `PULLBACK_PIPS`.
`TP_BB_RATIO` scales the Bollinger band width when deriving a fallback take-profit target. For example, `0.6` uses 60% of the band width.
`RANGE_ENTRY_OFFSET_PIPS` determines how far from the Bollinger band center price must be (in pips) before keeping a market entry. When closer, the entry switches to a LIMIT at the band high or low. The default is `3`.
`想定ノイズ` is automatically computed from ATR and Bollinger Band width and included in the AI prompt to help choose wider stop-loss levels.
The indicators module also calculates `adx_bb_score`, a composite value derived from ADX changes and Bollinger Band width. This score is passed to the AI so it can gauge momentum strength from multiple angles.
`NOISE_SL_MULT` は AI が算出した SL をこの倍率で拡大します (default `1.5`).
`BE_VOL_ADX_MIN` と `BE_VOL_SL_MULT` を設定すると、ブレイクイーブン発動時に ADX
がこの値以上なら SL を `entry_price ± ATR × BE_VOL_SL_MULT` に調整します。
`PATTERN_NAMES` lists chart pattern names passed to the AI or local scanner for detection, e.g. `double_bottom,double_top,doji`.
`LOCAL_WEIGHT_THRESHOLD` は 0〜1 の値で、ローカル判定と AI 判定の整合度スコアがこの値以上ならローカルを、未満なら AI を優先します。`USE_LOCAL_PATTERN` を `true` にすると常にローカル検出のみを使用し、`settings.env` のデフォルト値も `true` です。
`PATTERN_MIN_BARS` でパターン完成に必要なローソク足の本数を、`PATTERN_TOLERANCE` で高値・安値の許容誤差を調整できます。
`PATTERN_EXCLUDE_TFS` に `M1` などを指定すると、その時間足ではパターン検出を行いません。
`PATTERN_TFS` を `M1,M5` のように設定すると、指定した時間足のみをスキャンします。
`STRICT_ENTRY_FILTER` controls whether the M1 RSI cross signal is required. Set to `false` to skip the cross check (default `true`).
`HIGHER_TF_ENABLED` を `true` にすると、上位足ピボットとの距離も TP 計算に利用します。
`VOL_MA_PERIOD` sets the averaging window for volume checks. If the average falls below `MIN_VOL_MA` (or `MIN_VOL_M1`) the entry is blocked.
`ADX_SLOPE_LOOKBACK` defines how many candles to look back when computing ADX slope, and `ADX_DYNAMIC_COEFF` scales the ADX threshold based on Bollinger width.
`EMA_FLAT_PIPS` determines the range treated as a flat EMA slope; convergence with a reversal within this range triggers the *急反転* filter.
`OVERSHOOT_ATR_MULT` blocks entries when price overshoots below the lower Bollinger Band by this multiple of ATR.
`STRICT_TF_ALIGN` enforces multi-timeframe EMA alignment before entering.

`TF_EMA_WEIGHTS` specifies the weight of each timeframe when evaluating EMA alignment, e.g. `M5:0.4,H1:0.3,H4:0.3`.
`AI_ALIGN_WEIGHT` adds the AI's suggested direction to the multi-timeframe alignment check.

`ALLOW_DELAYED_ENTRY` set to `true` lets the AI return `"mode":"wait"` when a trend is overextended. The job runner will keep polling and enter once the pullback depth is satisfied.

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

The API exposes endpoints for status checks, a simple dashboard and runtime settings. Start it with Uvicorn:
```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port 8080
```

## LINE 通知設定

API から LINE にメッセージを送信するには、まず `.env` に以下の環境変数を設定します。

```bash
LINE_CHANNEL_TOKEN=<your_line_token>
LINE_USER_ID=<your_line_user_id>
```

次のコマンドで API を起動してください。

```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port 8080
```

テスト用エンドポイント `/notifications/send` を利用すると送信確認ができます。

```bash
curl -X POST http://localhost:8080/notifications/send
```

設定画面や `/notifications/settings` からトークンとユーザー ID を更新すると
環境変数にも反映され、即座に送信処理に利用されます。

## Running the Job Scheduler

The job runner performs market data collection, indicator calculation and trading decisions. Run it directly with Python:
```bash
python3 -m backend.scheduler.job_runner
```
If the optional performance logger was added earlier, each job loop's timing
will be appended to `backend/logs/perf_stats.jsonl`.

Both services can also be launched via Docker using `Dockerfile.api` and `Dockerfile.job` respectively.

### Apple Silicon (ARM) users

If you are on an M1/M2 Mac or other ARM-based machine, build the images for
the `linux/amd64` platform so they run correctly:

```bash
docker build --platform linux/amd64 -f Dockerfile .
```

Use the same flag when building `backend/Dockerfile.api` or
`backend/Dockerfile.job`. Note that running these x86 containers under
emulation can be slower and some dependencies may not behave exactly the same
as on native x86 hardware.

## Database

Trade history is stored in `trades.db` (SQLite) at the repository root by default.
You can override the path with the environment variable `TRADES_DB_PATH`.
When running inside Docker this defaults to `/app/trades.db`.

SQLite uses WAL (Write-Ahead Logging) mode. For existing databases run:
```bash
sqlite3 trades.db "PRAGMA journal_mode=WAL;"
```


The table now includes an `ai_response` column which stores the full text returned
by the AI when opening or closing a trade.

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

## React UI

The active React application lives in `piphawk-ui/` and was bootstrapped with Create React App. Run it locally with:

```bash
cd piphawk-ui
npm install
npm start
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
