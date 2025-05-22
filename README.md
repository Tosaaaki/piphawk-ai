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
3. **Environment variables**
   Copy the sample configuration files and edit them with your credentials:
   ```bash
   cp backend/config/secret.env .env
   cp backend/config/settings.env .
   ```
   Edit `.env` and set `OPENAI_API_KEY`, `OANDA_API_KEY` and `OANDA_ACCOUNT_ID`.
   The application automatically loads `.env`, `backend/config/settings.env` and
   `backend/config/secret.env` once at startup using `backend.utils.env_loader`.
   Adjust any values in `settings.env` as needed.
   `RANGE_CENTER_BLOCK_PCT` controls how close to the Bollinger band center price
   can be when ADX is below `ADX_RANGE_THRESHOLD`. Set to `0.3` (30%) to block
   entries near the middle of a range, helping suppress counter-trend trades.
 `AI_PROFIT_TRIGGER_RATIO` defines what portion of the take-profit target must
 be reached before an AI exit check occurs. The default value is `0.3` (30%).
`PULLBACK_LIMIT_OFFSET_PIPS` is the base distance for a pullback LIMIT order when the AI proposes a market entry. The actual offset is derived from ATR and ADX, and if price runs away while the trend persists the order can be switched to a market order under AI control.
`AI_LIMIT_CONVERT_MODEL` sets the OpenAI model used when asking whether a pending LIMIT should be switched to a market order. The default is `gpt-4o-mini`.
`PULLBACK_PIPS` defines the offset used specifically when the price is within the pivot suppression range. The defaults are `2` and `3` respectively.
`想定ノイズ` is automatically computed from ATR and Bollinger Band width and included in the AI prompt to help choose wider stop-loss levels.
`PATTERN_NAMES` lists chart pattern names passed to the AI or local scanner for detection, e.g. `double_bottom,double_top,doji`.
`USE_LOCAL_PATTERN` を `true` にすると、AI を使わずローカルの `pattern_scanner` でチャートパターンを判定します。デフォルトは `false` です。
`PATTERN_MIN_BARS` でパターン完成に必要なローソク足の本数を、`PATTERN_TOLERANCE` で高値・安値の許容誤差を調整できます。
`PATTERN_EXCLUDE_TFS` に `M1` などを指定すると、その時間足ではパターン検出を行いません。

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

`USE_LOCAL_PATTERN=true` を設定すると、OpenAI を使用せずローカル判定を行います。
ローカル判定時は `pattern_scanner.scan()` を使うことで複数時間足のローソク足データ
から時間足ごとの検出結果を得られます。

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
