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
   python -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```
   The indicator modules require **pandas**. If it is not installed, add it with:
   ```bash
   pip install pandas
   ```
3. **Environment variables**
   最初にテンプレートをコピーし、自分用の `.env` または `backend/config/secret.env` を作成します。
   ```bash
   cp backend/config/secret.env .env
   cp backend/config/settings.env .
   # Edit .env and set OPENAI_API_KEY, OANDA_API_KEY and OANDA_ACCOUNT_ID
   ```
   アプリケーションは `.env`, `backend/config/settings.env`, `backend/config/secret.env` の順で環境変数を読み込みます。
   必要に応じて `settings.env` の値も調整してください。
   `RANGE_CENTER_BLOCK_PCT` controls how close to the Bollinger band center price
   can be when ADX is below `ADX_RANGE_THRESHOLD`. Set to `0.3` (30%) to block
   entries near the middle of a range, helping suppress counter-trend trades.
   `BAND_WIDTH_THRESH_PIPS` defines the Bollinger band width that triggers
   range mode regardless of ADX. When the width falls below this value the system
   treats the market as ranging and the AI prompt notes that *BB width is
   contracting*.
`AI_PROFIT_TRIGGER_RATIO` defines what portion of the take-profit target must
be reached before an AI exit check occurs. The default value is `0.5` (50%).
`MIN_RRR` sets the minimum reward-to-risk ratio allowed when selecting a
take-profit. The TP level is now chosen to maximise expected value while
keeping the ratio at or above this threshold.
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
`NOISE_SL_MULT` は AI が算出した SL をこの倍率で拡大します (default `1.5`).
`PATTERN_NAMES` lists chart pattern names passed to the AI or local scanner for detection, e.g. `double_bottom,double_top,doji`.
`LOCAL_WEIGHT_THRESHOLD` は 0〜1 の値で、ローカル判定と AI 判定の整合度スコアがこの値以上ならローカルを、未満なら AI を優先します。旧 `USE_LOCAL_PATTERN` は廃止されました。
`PATTERN_MIN_BARS` でパターン完成に必要なローソク足の本数を、`PATTERN_TOLERANCE` で高値・安値の許容誤差を調整できます。
`PATTERN_EXCLUDE_TFS` に `M1` などを指定すると、その時間足ではパターン検出を行いません。
`PATTERN_TFS` を `M1,M5` のように設定すると、指定した時間足のみをスキャンします。
`STRICT_ENTRY_FILTER` controls whether the M1 RSI cross signal is required. Set to `false` to skip the cross check (default `true`).
`HIGHER_TF_ENABLED` を `true` にすると、上位足ピボットとの距離も TP 計算に利用します。

## Running the API

The API exposes endpoints for status checks, a simple dashboard and runtime settings. Start it with Uvicorn:
```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port 8080
```

## Running the Job Scheduler

The job runner performs market data collection, indicator calculation and trading decisions. Run it directly with Python:
```bash
python -m backend.scheduler.job_runner
```

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

Trade history is stored in `trades.db` (SQLite) at the repository root. This file is no longer tracked in Git. A pre-populated example is available in `backend/logs/` and is copied to `/app/trades.db` when running inside Docker.

The table now includes an `ai_response` column which stores the full text returned
by the AI when opening or closing a trade.

If you need a clean database locally, either copy the example file:

```bash
cp backend/logs/trades.db trades.db
```

or create a fresh one using the helper in `backend.logs.log_manager`:

```bash
python - <<'EOF'
from backend.logs.log_manager import init_db
init_db()
EOF
```
This helper also upgrades older databases to include the new `ai_response`
column. See `docs/db_migration.md` for details.

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

`LOCAL_WEIGHT_THRESHOLD` を調整することで、AI 判定とローカル判定のどちらを優先するかを決められます。ローカルの結果だけを使いたい場合は `1.0` に設定してください。
ローカル判定を行うには `pattern_scanner.scan()` を利用します。

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
