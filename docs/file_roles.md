# File Roles

このドキュメントでは、リポジトリ直下にある主なファイルやディレクトリの役割を簡単に説明します。

| パス | 役割 |
| --- | --- |
| `.dockerignore` | Docker ビルドで除外するファイル一覧 |
| `.env.template` | 環境変数ファイルのテンプレート |
| `.git/` | Git リポジトリメタデータ |
| `.github/` | GitHub ワークフロー設定 |
| `.gitignore` | Git で無視するファイル定義 |
| `.markdownlint-cli2.yaml` | Markdownlint 設定 |
| `.markdownlintignore` | Markdownlint 除外設定 |
| `AGENTS.md` | 開発ルールやテスト手順の説明 |
| `CHANGELOG.md` | 変更履歴 |
| `Dockerfile` | バックエンド用 Docker イメージ定義 |
| `LICENSE` | ライセンス情報 |
| `README.md` | プロジェクト概要とセットアップ手順 |
| `ai/` | AI 関連モジュール群 |
| `analysis/` | 市場分析スクリプトとユーティリティ |
| `backend/` | FastAPI サーバーとジョブランナー |
| `benchmarks/` | ベンチマーク用コード |
| `config/` | YAML 設定ファイル |
| `core/` | エントリー・エグジットの基盤ロジック |
| `deploy.sh` | デプロイ補助スクリプト |
| `diagnostics/` | 動作診断やログ解析ツール |
| `docker-compose.yml` | Docker Compose 定義 |
| `docs/` | ドキュメント群 |
| `execution/` | 約定処理を含む実行モジュール |
| `fast_metrics.py` | Prometheus 用メトリクス取得スクリプト |
| `indicators/` | テクニカル指標モジュール |
| `maintenance/` | メンテナンススクリプト |
| `models/` | 機械学習モデル関連ファイル |
| `monitoring/` | モニタリングと通知処理 |
| `pipelines/` | 分析・取引パイプライン定義 |
| `piphawk-ui/` | React 製フロントエンド |
| `piphawk_ai/` | Job Runner 本体と戦略実装 |
| `prompts/` | OpenAI へのプロンプトテンプレート |
| `pyproject.toml` | Python プロジェクト設定 |
| `pytest.ini` | Pytest 設定ファイル |
| `regime/` | 市場レジーム分析モジュール |
| `requirements-dev.txt` | 開発用依存ライブラリ一覧 |
| `requirements-test.txt` | テスト用依存ライブラリ一覧 |
| `risk/` | ポートフォリオリスク管理 |
| `run_tests.sh` | テスト実行スクリプト |
| `selector_fast.py` | 高速モード判定ツール |
| `signals/` | 取引シグナル生成処理 |
| `sql/` | SQL スクリプトやDB関連ファイル |
| `strategies/` | 取引戦略モジュール |
| `tests/` | 単体テストコード |
| `training/` | 学習・検証用スクリプト |

## 主要 Python ファイル

下記はディレクトリ内でも特に重要な Python スクリプトの例です。

| パス | 役割 |
| --- | --- |
| `ai/local_model.py` | ローカル LLM を利用するためのインターフェース |
| `analysis/ai_strategy.py` | AI による取引戦略のエントリーポイント |
| `backend/api/main.py` | FastAPI サーバーの起動スクリプト |
| `execution/scalp_manager.py` | スキャルピング実行の管理処理 |
| `piphawk_ai/main.py` | ジョブランナー全体を起動するメイン処理 |
| `piphawk_ai/runner/entry.py` | 各戦略のエントリー判断ロジック |
| `core/ring_buffer.py` | ティックデータを保持するリングバッファ実装 |

## Python ファイル一覧

以下はリポジトリに含まれる Python ファイルと、それぞれの簡単な説明です。

| Path | Description |
| --- | --- |
| `ai/__init__.py` | パッケージ初期化ファイル |
| `ai/local_model.py` | OpenAI 互換のローカルモデル呼び出しラッパー |
| `ai/macro_analyzer.py` | FRED と GDELT からニュースを取得して要約するモジュール |
| `ai/policy_trainer.py` | Offline RL trainer for strategy selection. |
| `ai/prompt_templates.py` | プロンプトテンプレート管理モジュール |
| `analysis/__init__.py` | trade_patterns からスコア計算関数 |
| `analysis/ai_strategy.py` | AI ストラテジー補助モジュール. |
| `analysis/backtest_utils.py` | Simple backtest helper. |
| `analysis/cluster_regime.py` | 学習済みクラスタリングモデルを用いたレジーム推定ヘルパー. |
| `analysis/detect_mode.py` | Local trade mode detection utilities. |
| `analysis/filter_statistics.py` | フィルター効果を集計する簡易スクリプト. |
| `analysis/llm_mode_selector.py` | LLM を用いたモード選択ラッパー. |
| `analysis/log_analysis.py` | Utility functions for log analysis. |
| `analysis/mode_detector.py` | Simple trade mode detector without LLM. |
| `analysis/mode_preclassifier.py` | 単純なADX/ATRベースの取引レジーム判定モジュール. |
| `analysis/regime_detector.py` | Range からトレンドへの移行を検知するモジュール. |
| `analysis/signal_filter.py` | Multi timeframe alignment checks. |
| `analysis/trade_patterns.py` | Trade pattern scoring utilities. |
| `backend/__init__.py` | プロジェクトルートを PYTHONPATH に追加 |
| `backend/analysis/__init__.py` | パッケージ初期化ファイル |
| `backend/analysis/param_performance.py` | Parameter change performance analysis. |
| `backend/api/__init__.py` | パッケージ初期化ファイル |
| `backend/api/main.py` | Return 200 OK with a tiny JSON payload. |
| `backend/api/test_control_endpoints.py` | control_endpoints のテスト |
| `backend/api/test_panic_stop.py` | panic_stop のテスト |
| `backend/api/test_recent_trades.py` | recent_trades のテスト |
| `backend/config/__init__.py` | パッケージ初期化ファイル |
| `backend/config/defaults.py` | Default configuration values for runtime. |
| `backend/core/__init__.py` | パッケージ初期化ファイル |
| `backend/core/ai_throttle.py` | AI call cooldown management. |
| `backend/data/__init__.py` | パッケージ初期化ファイル |
| `backend/filters/__init__.py` | General entry filter helpers. |
| `backend/filters/breakout_entry.py` | Breakout entry filter. |
| `backend/filters/extension_block.py` | Prevent entries when price is extended far from EMA. |
| `backend/filters/false_break_filter.py` | False break detection filter. |
| `backend/filters/h1_level_block.py` | H1 support/resistance level block filter. |
| `backend/filters/scalp_entry.py` | スキャルプ用エントリーフィルター. |
| `backend/filters/trend_pullback.py` | Trend pullback entry filter. |
| `backend/filters/volatility_filter.py` | Volatility and breakout filter. |
| `backend/indicators/__init__.py` | パッケージ初期化ファイル |
| `backend/indicators/adx.py` | Average Directional Movement Index (ADX) implementation. |
| `backend/indicators/atr.py` | Calculate the Average True Range (ATR) for given price data. |
| `backend/indicators/calculate_indicators.py` | Return percentile rank of ``value`` within ``series`` (0-100). |
| `backend/indicators/candle_features.py` | Return simple moving average of volumes. |
| `backend/indicators/ema.py` | Calculate the Exponential Moving Average (EMA) for a given list or Series of prices. |
| `backend/indicators/keltner.py` | Simple Keltner Channel implementation. |
| `backend/indicators/macd.py` | Return MACD line and signal line. |
| `backend/indicators/n_wave.py` | Return projected N-wave target price if detectable. |
| `backend/indicators/pivot.py` | Return classic floor-trader pivot levels. |
| `backend/indicators/polarity.py` | Return rolling polarity score between -1 and 1. |
| `backend/indicators/rolling.py` | Rolling indicator utilities using deque for efficiency. |
| `backend/indicators/rsi.py` | Rsi モジュール |
| `backend/indicators/vwap_band.py` | Return VWAP for given price and volume series. |
| `backend/logs/__init__.py` | パッケージ初期化ファイル |
| `backend/logs/cleanup.py` | データベースをVACUUMして不要領域を解放する |
| `backend/logs/daily_summary.py` | SELECT instrument, close_price, tp_price, units, close_time |
| `backend/logs/exit_logger.py` | append JSON data to exit_log.jsonl |
| `backend/logs/fetch_oanda_trades.py` | env_loader automatically loads default env files at import time |
| `backend/logs/info_logger.py` | Log formatted INFO message. |
| `backend/logs/initial_fetch_oanda_trades.py` | UPDATE oanda_trades |
| `backend/logs/log_manager.py` | Return the current database path. |
| `backend/logs/perf_stats_logger.py` | Simple performance logging utility. |
| `backend/logs/reconcile_trades.py` | Convert ISO string to aware UTC datetime. |
| `backend/logs/show_param_history.py` | param_changes テーブルから履歴を取得する |
| `backend/logs/show_tables.py` | Return list of table names. |
| `backend/logs/trade_logger.py` | Wrapper for log_trade allowing ``ExitReason`` enumeration and RL logging. |
| `backend/logs/update_oanda_trades.py` | Retry database operations when the database is locked. |
| `backend/main.py` | Convenience entry point for running Piphawk components. |
| `backend/market_data/__init__.py` | パッケージ初期化ファイル |
| `backend/market_data/candle_fetcher.py` | Fetch candlestick data from OANDA API. |
| `backend/market_data/tick_fetcher.py` | Fetch the latest tick (pricing) data from the OANDA API. |
| `backend/market_data/tick_metrics.py` | Tick-based metric calculations. |
| `backend/market_data/tick_stream.py` | OANDA streaming client via HTTP long polling. |
| `backend/orders/__init__.py` | Order manager factory. |
| `backend/orders/mock_order_manager.py` | Paper trading mock order manager. |
| `backend/orders/order_manager.py` | Extract errorCode and errorMessage from a requests.Response. |
| `backend/orders/position_manager.py` | Return current marginUsed from account summary. |
| `backend/reentry_manager.py` | SL直後の再エントリー判定を行うヘルパー。 |
| `backend/risk_manager.py` | ATRとの比較に基づきSLが適切か検証する。 |
| `backend/scheduler/__init__.py` | パッケージ初期化ファイル |
| `backend/scheduler/job_runner.py` | Run the selected pipeline based on USE_VOTE_PIPELINE. |
| `backend/scheduler/policy_updater.py` | Background updater for offline policy files. |
| `backend/scheduler/strategy_selector.py` | Strategy selection using LinUCB with optional offline policy. |
| `backend/strategy/__init__.py` | パッケージ初期化ファイル |
| `backend/strategy/dynamic_pullback.py` | Dynamic pullback threshold calculation. |
| `backend/strategy/entry_ai_decision.py` | DEPRECATED MODULE |
| `backend/strategy/entry_logic.py` | Return limit price offset by given pips in the direction of a pullback. |
| `backend/strategy/exit_ai_decision.py` | AI‑based exit decision module. |
| `backend/strategy/exit_logic.py` | Generate a prompt describing the current position, market data, and indicators for AI analysis. |
| `backend/strategy/false_break_filter.py` | False breakout detection utilities. |
| `backend/strategy/higher_tf_analysis.py` | higher_tf_analysis.py |
| `backend/strategy/llm_exit.py` | AI-driven exit adjustment helper. |
| `backend/strategy/momentum_follow.py` | ブレイク後のモメンタムを利用した追随エントリー判定用モジュール. |
| `backend/strategy/openai_analysis.py` | OpenAIモデルを用いたトレード分析ユーティリティ |
| `backend/strategy/openai_micro_scalp.py` | Return prompt text for micro-scalp analysis. |
| `backend/strategy/openai_prompt.py` | Prompt generation utilities for OpenAI analysis. |
| `backend/strategy/openai_scalp_analysis.py` | Return the last ``n`` values from a pandas Series or list. |
| `backend/strategy/pattern_ai_detection.py` | Detect chart patterns using OpenAI. |
| `backend/strategy/pattern_scanner.py` | Convert candle data to a standard list of OHLC dictionaries. |
| `backend/strategy/range_break.py` | Detect if the latest candle closed outside the recent range. |
| `backend/strategy/reentry_manager.py` | Manage cooldown after stop-loss exits. |
| `backend/strategy/risk_manager.py` | Risk management helper functions. |
| `backend/strategy/selector.py` | RL ポリシーに基づく戦略セレクタ. |
| `backend/strategy/signal_filter.py` | 軽量シグナル・フィルター |
| `backend/strategy/strategy_analyzer.py` | .envファイルから戦略パラメータを読み込む |
| `backend/strategy/validators.py` | Helper functions for validating AI trade plans. |
| `backend/tests/__init__.py` | __init__ のテスト |
| `backend/tests/test_adjust_tp_sl.py` | adjust_tp_sl のテスト |
| `backend/tests/test_adx_bb_score.py` | adx_bb_score のテスト |
| `backend/tests/test_adx_slope_bias.py` | adx_slope_bias のテスト |
| `backend/tests/test_ai_cooldown.py` | ai_cooldown のテスト |
| `backend/tests/test_ai_decision_logging.py` | ai_decision_logging のテスト |
| `backend/tests/test_ai_throttle.py` | ai_throttle のテスト |
| `backend/tests/test_align_adx_weight.py` | align_adx_weight のテスト |
| `backend/tests/test_align_bypass.py` | align_bypass のテスト |
| `backend/tests/test_atr_boost_detector.py` | atr_boost_detector のテスト |
| `backend/tests/test_atr_breakout.py` | atr_breakout のテスト |
| `backend/tests/test_atr_tp_sl_mult.py` | atr_tp_sl_mult のテスト |
| `backend/tests/test_be_volatility_sl.py` | be_volatility_sl のテスト |
| `backend/tests/test_breakout_entry.py` | breakout_entry のテスト |
| `backend/tests/test_candle_fetcher.py` | candle_fetcher のテスト |
| `backend/tests/test_candle_summary.py` | candle_summary のテスト |
| `backend/tests/test_climax_detection.py` | climax_detection のテスト |
| `backend/tests/test_composite_threshold.py` | composite_threshold のテスト |
| `backend/tests/test_consecutive_high_low.py` | consecutive_high_low のテスト |
| `backend/tests/test_consistency_normalization.py` | consistency_normalization のテスト |
| `backend/tests/test_consistency_weights.py` | consistency_weights のテスト |
| `backend/tests/test_cooldown_refresh.py` | cooldown_refresh のテスト |
| `backend/tests/test_counter_trend_block.py` | counter_trend_block のテスト |
| `backend/tests/test_duplicate_entry_prevention.py` | duplicate_entry_prevention のテスト |
| `backend/tests/test_dynamic_pullback.py` | dynamic_pullback のテスト |
| `backend/tests/test_dynamic_sl.py` | dynamic_sl のテスト |
| `backend/tests/test_early_exit_threshold.py` | early_exit_threshold のテスト |
| `backend/tests/test_entry_break_override.py` | entry_break_override のテスト |
| `backend/tests/test_entry_confidence.py` | entry_confidence のテスト |
| `backend/tests/test_entry_cost_guard.py` | entry_cost_guard のテスト |
| `backend/tests/test_entry_decline_cancel.py` | entry_decline_cancel のテスト |
| `backend/tests/test_entry_filter_rsi.py` | entry_filter_rsi のテスト |
| `backend/tests/test_entry_regime_logging.py` | entry_regime_logging のテスト |
| `backend/tests/test_entry_skip_logging.py` | entry_skip_logging のテスト |
| `backend/tests/test_env_loader.py` | env_loader のテスト |
| `backend/tests/test_exit_bias_factor.py` | exit_bias_factor のテスト |
| `backend/tests/test_exit_cooldown.py` | exit_cooldown のテスト |
| `backend/tests/test_exit_logic_high_atr_low_adx.py` | exit_logic_high_atr_low_adx のテスト |
| `backend/tests/test_exit_pattern_override.py` | exit_pattern_override のテスト |
| `backend/tests/test_exit_pips_symmetry.py` | exit_pips_symmetry のテスト |
| `backend/tests/test_exit_reason_logging.py` | exit_reason_logging のテスト |
| `backend/tests/test_exit_serialization.py` | exit_serialization のテスト |
| `backend/tests/test_exit_trade_market_close.py` | exit_trade_market_close のテスト |
| `backend/tests/test_extension_block.py` | extension_block のテスト |
| `backend/tests/test_fallback_dynamic_risk.py` | fallback_dynamic_risk のテスト |
| `backend/tests/test_false_break_filter.py` | false_break_filter のテスト |
| `backend/tests/test_follow_breakout_call.py` | follow_breakout_call のテスト |
| `backend/tests/test_follow_through.py` | follow_through のテスト |
| `backend/tests/test_h1_level_block.py` | h1_level_block のテスト |
| `backend/tests/test_higher_tf_override.py` | higher_tf_override のテスト |
| `backend/tests/test_higher_tf_pivot.py` | higher_tf_pivot のテスト |
| `backend/tests/test_higher_tf_prompt.py` | higher_tf_prompt のテスト |
| `backend/tests/test_higher_tf_tp.py` | higher_tf_tp のテスト |
| `backend/tests/test_job_runner_env_mode.py` | job_runner_env_mode のテスト |
| `backend/tests/test_job_runner_handles_none_indicators.py` | job_runner_handles_none_indicators のテスト |
| `backend/tests/test_job_runner_restore_mode.py` | job_runner_restore_mode のテスト |
| `backend/tests/test_job_runner_tp_flags.py` | job_runner_tp_flags のテスト |
| `backend/tests/test_keltner.py` | keltner のテスト |
| `backend/tests/test_limit_retry.py` | limit_retry のテスト |
| `backend/tests/test_llm_exit_adjustment.py` | llm_exit_adjustment のテスト |
| `backend/tests/test_lower_tf_weight.py` | lower_tf_weight のテスト |
| `backend/tests/test_macd.py` | macd のテスト |
| `backend/tests/test_market_condition_break.py` | market_condition_break のテスト |
| `backend/tests/test_market_condition_cooldown.py` | market_condition_cooldown のテスト |
| `backend/tests/test_market_condition_fallback.py` | market_condition_fallback のテスト |
| `backend/tests/test_market_condition_override.py` | market_condition_override のテスト |
| `backend/tests/test_market_di_cross_float.py` | market_di_cross_float のテスト |
| `backend/tests/test_min_hold_exit.py` | min_hold_exit のテスト |
| `backend/tests/test_n_wave.py` | n_wave のテスト |
| `backend/tests/test_no_pullback_prompt.py` | no_pullback_prompt のテスト |
| `backend/tests/test_noise_prompt.py` | noise_prompt のテスト |
| `backend/tests/test_openai_cache_limit.py` | openai_cache_limit のテスト |
| `backend/tests/test_partial_close.py` | partial_close のテスト |
| `backend/tests/test_pattern_ai_detection.py` | pattern_ai_detection のテスト |
| `backend/tests/test_pattern_detection.py` | pattern_detection のテスト |
| `backend/tests/test_pattern_prompt.py` | pattern_prompt のテスト |
| `backend/tests/test_pattern_scanner.py` | pattern_scanner のテスト |
| `backend/tests/test_peak_entry.py` | peak_entry のテスト |
| `backend/tests/test_pivot_calc.py` | pivot_calc のテスト |
| `backend/tests/test_pivot_suppression.py` | pivot_suppression のテスト |
| `backend/tests/test_polarity_exit.py` | polarity_exit のテスト |
| `backend/tests/test_price_format.py` | price_format のテスト |
| `backend/tests/test_price_formatting.py` | price_formatting のテスト |
| `backend/tests/test_prob_validation.py` | prob_validation のテスト |
| `backend/tests/test_prompt_bias.py` | prompt_bias のテスト |
| `backend/tests/test_prompt_m15.py` | prompt_m15 のテスト |
| `backend/tests/test_pullback_bypass.py` | pullback_bypass のテスト |
| `backend/tests/test_pullback_limit.py` | pullback_limit のテスト |
| `backend/tests/test_pullback_prompt.py` | pullback_prompt のテスト |
| `backend/tests/test_range_break_alert.py` | range_break_alert のテスト |
| `backend/tests/test_range_break_detection.py` | range_break_detection のテスト |
| `backend/tests/test_range_index_series.py` | range_index_series のテスト |
| `backend/tests/test_rapid_reversal_block.py` | rapid_reversal_block のテスト |
| `backend/tests/test_recent_candle_bias.py` | recent_candle_bias のテスト |
| `backend/tests/test_reconcile_trades.py` | reconcile_trades のテスト |
| `backend/tests/test_reentry_manager.py` | reentry_manager のテスト |
| `backend/tests/test_regime_breakout_entry_method.py` | regime_breakout_entry_method のテスト |
| `backend/tests/test_regime_caching.py` | regime_caching のテスト |
| `backend/tests/test_regime_cross_delay.py` | regime_cross_delay のテスト |
| `backend/tests/test_regime_detector.py` | regime_detector のテスト |
| `backend/tests/test_regime_filters.py` | regime_filters のテスト |
| `backend/tests/test_regime_override.py` | regime_override のテスト |
| `backend/tests/test_reversal_exit.py` | reversal_exit のテスト |
| `backend/tests/test_risk_expected_value.py` | risk_expected_value のテスト |
| `backend/tests/test_risk_manager.py` | risk_manager のテスト |
| `backend/tests/test_rrr_enforcement.py` | rrr_enforcement のテスト |
| `backend/tests/test_scale_constraints.py` | scale_constraints のテスト |
| `backend/tests/test_scale_entry.py` | scale_entry のテスト |
| `backend/tests/test_scalp_cond_tf.py` | scalp_cond_tf のテスト |
| `backend/tests/test_scalp_mode.py` | scalp_mode のテスト |
| `backend/tests/test_short_sl_price.py` | short_sl_price のテスト |
| `backend/tests/test_signal_manager.py` | signal_manager のテスト |
| `backend/tests/test_signal_manager_breakout.py` | signal_manager_breakout のテスト |
| `backend/tests/test_spread_check.py` | spread_check のテスト |
| `backend/tests/test_tf_weight_normalization.py` | tf_weight_normalization のテスト |
| `backend/tests/test_tp_bb_ratio.py` | tp_bb_ratio のテスト |
| `backend/tests/test_tp_extension.py` | tp_extension のテスト |
| `backend/tests/test_tp_ratio.py` | tp_ratio のテスト |
| `backend/tests/test_tp_reduction.py` | tp_reduction のテスト |
| `backend/tests/test_trade_plan_parse_error.py` | trade_plan_parse_error のテスト |
| `backend/tests/test_trailing_calendar.py` | trailing_calendar のテスト |
| `backend/tests/test_trailing_stop_abs.py` | trailing_stop_abs のテスト |
| `backend/tests/test_trend_pullback.py` | trend_pullback のテスト |
| `backend/tests/test_update_trade_sl.py` | update_trade_sl のテスト |
| `backend/tests/test_volatility_filter.py` | volatility_filter のテスト |
| `backend/tests/test_vwap_band.py` | vwap_band のテスト |
| `backend/tests/test_weight_last.py` | weight_last のテスト |
| `backend/utils/__init__.py` | パッケージ初期化ファイル |
| `backend/utils/ai_parse.py` | Safely parse an OpenAI answer that may be a dict or JSON string. |
| `backend/utils/async_helper.py` | 非同期関数を同期的に実行するユーティリティ |
| `backend/utils/db_helper.py` | Simple SQLite helper utilities. |
| `backend/utils/env_loader.py` | Utility functions for environment variable management. |
| `backend/utils/http_client.py` | HTTPリクエストをリトライ付きで実行するユーティリティ |
| `backend/utils/notification.py` | Utility module for outbound LINE notifications. |
| `backend/utils/oanda_client.py` | OANDA helper – pending LIMIT order lookup |
| `backend/utils/openai_client.py` | Thin wrapper around the OpenAI client with optional lazy import. |
| `backend/utils/price.py` | Utility helpers for price formatting / rounding before sending orders |
| `backend/utils/prompt_loader.py` | Prompt template loader utility. |
| `backend/utils/restart_guard.py` | Restart guard to prevent excessive self-restarts. |
| `backend/utils/trade_time.py` | Utility helper for trade timestamps. |
| `benchmarks/bench_tick_pipeline.py` | 簡易ティックパイプラインベンチマーク. |
| `config/__init__.py` | Package initialization for config |
| `config/params_loader.py` | Load parameters from params.yaml and strategy.yml into environment variables. |
| `core/__init__.py` | コアユーティリティをまとめたモジュール. |
| `core/ring_buffer.py` | 固定長リングバッファ. |
| `diagnostics/__init__.py` | パッケージ初期化ファイル |
| `diagnostics/diagnostics.py` | CREATE TABLE IF NOT EXISTS diagnostics ( |
| `diagnostics/view_logs.py` | View logs モジュール |
| `execution/__init__.py` | パッケージ初期化ファイル |
| `execution/scalp_manager.py` | Scalp trade management. |
| `execution/sync_manager.py` | Update trade exits using OANDA history. |
| `fast_metrics.py` | 軽量な指標計算モジュール. |
| `indicators/__init__.py` | Indicator helpers for trading signals. |
| `indicators/bollinger.py` | 複数の時間軸に対応したボリンジャーバンドのユーティリティ。 |
| `indicators/candlestick.py` | Return the upper shadow ratio of a candle. |
| `indicators/patterns.py` | Detect double-bottom pattern and compute features. |
| `indicators/volatility.py` | Utility functions for volatility measurements. |
| `maintenance/__init__.py` | Package initialization for maintenance |
| `maintenance/disk_guard.py` | Call this from your main loop (or run standalone). |
| `maintenance/system_cleanup.py` | System maintenance script |
| `monitoring/__init__.py` | 監視機能を提供するサブモジュール. |
| `monitoring/metrics_publisher.py` | Kafka と Prometheus へメトリクスを送信するユーティリティ. |
| `monitoring/safety_trigger.py` | 損失やエラー発生数を監視して安全停止を行うためのモジュール. |
| `pipelines/walk_forward/eval_kpi.py` | Evaluate KPI and decide retrain flag. |
| `pipelines/walk_forward/run_walk_forward.py` | Walk-forward optimization main script. |
| `pipelines/walk_forward/utils.py` | Utility functions for simple walk-forward trading. |
| `piphawk_ai/__init__.py` | Namespace package for piphawk AI. |
| `piphawk_ai/main.py` | Main モジュール |
| `piphawk_ai/policy/offline.py` | Offline reinforcement learning policy loader. |
| `piphawk_ai/risk/cvar.py` | Wrapper for CVaR calculation utilities. |
| `piphawk_ai/risk/manager.py` | CVaR-based portfolio risk management. |
| `piphawk_ai/runner/__init__.py` | Runner package. |
| `piphawk_ai/runner/core.py` | Compose a minimal context dict for AI exit evaluation. |
| `piphawk_ai/runner/entry.py` | Entry-related helpers for JobRunner. |
| `piphawk_ai/runner/exit.py` | Exit-related helpers for JobRunner. |
| `piphawk_ai/tech_arch/__init__.py` | Technical entry pipeline package. |
| `piphawk_ai/tech_arch/ai_decision.py` | OpenAI decision helper for the M5 pipeline. |
| `piphawk_ai/tech_arch/entry_gate.py` | LLM entry gate for the technical pipeline. |
| `piphawk_ai/tech_arch/indicator_engine.py` | Indicator calculation helpers. |
| `piphawk_ai/tech_arch/m5_entry.py` | M5 signal detection helpers. |
| `piphawk_ai/tech_arch/market_classifier.py` | Simple market classification utilities. |
| `piphawk_ai/tech_arch/market_context.py` | Market snapshot utilities for the technical pipeline. |
| `piphawk_ai/tech_arch/mode_detector.py` | Wrapper around detect_mode for the technical pipeline. |
| `piphawk_ai/tech_arch/pipeline.py` | M5 technical entry pipeline orchestrator. |
| `piphawk_ai/tech_arch/post_filters.py` | Final safety checks for the technical pipeline. |
| `piphawk_ai/tech_arch/prefilters.py` | Prefilter utilities for the technical pipeline. |
| `piphawk_ai/tech_arch/risk_filters.py` | Basic risk filters for the technical pipeline. |
| `piphawk_ai/tech_arch/rule_validator.py` | Simple rule validator for entry plans. |
| `piphawk_ai/vote_arch/__init__.py` | Majority-vote trading pipeline components. |
| `piphawk_ai/vote_arch/ai_entry_plan.py` | Deterministic entry plan generation via OpenAI. |
| `piphawk_ai/vote_arch/ai_strategy_selector.py` | Select trade strategy via OpenAI and majority vote. |
| `piphawk_ai/vote_arch/entry_buffer.py` | Simple vertical ensemble buffer for entry plans. |
| `piphawk_ai/vote_arch/market_air_sensor.py` | Calculate market air index used in prompts. |
| `piphawk_ai/vote_arch/pipeline.py` | Orchestration pipeline for the majority-vote trading architecture. |
| `piphawk_ai/vote_arch/post_filters.py` | Final safety checks for entry plans. |
| `piphawk_ai/vote_arch/regime_detector.py` | Simple rule-based regime detection. |
| `piphawk_ai/vote_arch/trade_mode_selector.py` | Select final trade mode with rule fallback. |
| `regime/__init__.py` | パッケージ初期化ファイル |
| `regime/features.py` | レジーム分類用の特徴量計算ヘルパー. |
| `regime/gmm_detector.py` | Gaussian Mixture Model によるレジーム認識クラス. |
| `regime/hdbscan_detector.py` | HDBSCAN によるレジーム認識クラス. |
| `risk/__init__.py` | パッケージ初期化ファイル |
| `risk/cvar.py` | CVaR (Expected Shortfall) 計算ユーティリティ. |
| `risk/manager.py` | CVaR-based portfolio risk management. |
| `risk/portfolio_risk_manager.py` | Backward compatibility for PortfolioRiskManager import. |
| `risk/tp_sl_manager.py` | TP/SL ratio adjustment utilities. |
| `risk/trade_guard.py` | Simple losing streak guard. |
| `selector_fast.py` | Entry rule selector with LinUCB. |
| `signals/__init__.py` | パッケージ初期化ファイル |
| `signals/adx_strategy.py` | ADX値に基づくシンプルなストラテジー切換ユーティリティ. |
| `signals/composite_mode.py` | Composite trade mode decision utility. |
| `signals/mode_params.py` | weights項目があれば合計1となるよう正規化する |
| `signals/regime_filter.py` | Regime conflict blocker. |
| `signals/scalp_momentum.py` | Scalp momentum utilities. |
| `signals/scalp_strategy.py` | Simple multi timeframe scalp utilities. |
| `signals/signal_manager.py` | シグナル管理モジュール. |
| `signals/trend_filter.py` | Multi timeframe EMA trend filter. |
| `strategies/__init__.py` | Strategy modules. |
| `strategies/bandit_manager.py` | Bandit based strategy manager. |
| `strategies/base.py` | Strategy base classes. |
| `strategies/context_builder.py` | Utility functions to build context vectors for strategy selection. |
| `strategies/scalp/entry_rules.py` | Scalp entry rules. |
| `strategies/scalp_strategy.py` | Simple scalp strategy wrapper. |
| `strategies/selector.py` | Backward compatibility wrapper for StrategySelector. |
| `strategies/trend_strategy.py` | Simple trend-follow strategy wrapper. |
| `tests/conftest.py` | conftest のテスト |
| `tests/test_adx_mode.py` | adx_mode のテスト |
| `tests/test_bollinger_regression.py` | bollinger_regression のテスト |
| `tests/test_composite_scoring.py` | composite_scoring のテスト |
| `tests/test_cvar.py` | cvar のテスト |
| `tests/test_double_bottom_signal.py` | double_bottom_signal のテスト |
| `tests/test_double_top_signal.py` | double_top_signal のテスト |
| `tests/test_entry_logic.py` | entry_logic のテスト |
| `tests/test_entry_rules.py` | entry_rules のテスト |
| `tests/test_fast_metrics.py` | fast_metrics のテスト |
| `tests/test_force_close.py` | force_close のテスト |
| `tests/test_forced_entry_bypass.py` | forced_entry_bypass のテスト |
| `tests/test_format_price.py` | format_price のテスト |
| `tests/test_gmm_detector.py` | gmm_detector のテスト |
| `tests/test_hdbscan_detector.py` | hdbscan_detector のテスト |
| `tests/test_indicators_extra.py` | indicators_extra のテスト |
| `tests/test_job_runner_tech_pipeline.py` | job_runner_tech_pipeline のテスト |
| `tests/test_job_runner_vote_arch.py` | job_runner_vote_arch のテスト |
| `tests/test_log_analysis.py` | log_analysis のテスト |
| `tests/test_metrics_publisher_basic.py` | metrics_publisher_basic のテスト |
| `tests/test_micro_scalp.py` | micro_scalp のテスト |
| `tests/test_mode_detector_cfg.py` | mode_detector_cfg のテスト |
| `tests/test_mode_selector.py` | mode_selector のテスト |
| `tests/test_overshoot_dynamic.py` | overshoot_dynamic のテスト |
| `tests/test_overshoot_window.py` | overshoot_window のテスト |
| `tests/test_params_loader_mode.py` | params_loader_mode のテスト |
| `tests/test_params_loader_scalp.py` | params_loader_scalp のテスト |
| `tests/test_params_loader_strategy.py` | params_loader_strategy のテスト |
| `tests/test_pipeline.py` | pipeline のテスト |
| `tests/test_portfolio_risk_manager.py` | portfolio_risk_manager のテスト |
| `tests/test_process_entry_return.py` | process_entry_return のテスト |
| `tests/test_prompt_log.py` | prompt_log のテスト |
| `tests/test_range_adx_count.py` | range_adx_count のテスト |
| `tests/test_ring_buffer.py` | ring_buffer のテスト |
| `tests/test_rule_selector.py` | rule_selector のテスト |
| `tests/test_safety_trigger.py` | safety_trigger のテスト |
| `tests/test_safety_trigger_basic.py` | safety_trigger_basic のテスト |
| `tests/test_scalp_manager.py` | scalp_manager のテスト |
| `tests/test_scalp_manager_dynamic_tp.py` | scalp_manager_dynamic_tp のテスト |
| `tests/test_scalp_manager_hold.py` | scalp_manager_hold のテスト |
| `tests/test_scalp_momentum_exit.py` | scalp_momentum_exit のテスト |
| `tests/test_scalp_strategy.py` | scalp_strategy のテスト |
| `tests/test_scalp_trailing_after_tp.py` | scalp_trailing_after_tp のテスト |
| `tests/test_strategy_selector.py` | strategy_selector のテスト |
| `tests/test_strategy_selector_dynamic.py` | strategy_selector_dynamic のテスト |
| `tests/test_strategy_selector_offline.py` | strategy_selector_offline のテスト |
| `tests/test_sync_manager.py` | sync_manager のテスト |
| `tests/test_tech_arch_flow.py` | tech_arch_flow のテスト |
| `tests/test_tech_arch_no_ai.py` | tech_arch_no_ai のテスト |
| `tests/test_trend_adx_thresh.py` | trend_adx_thresh のテスト |
| `tests/test_trend_strategy.py` | trend_strategy のテスト |
| `tests/test_update_oanda_trades_logs.py` | update_oanda_trades_logs のテスト |
| `tests/test_validators.py` | validators のテスト |
| `tests/test_volume_ratio.py` | volume_ratio のテスト |
| `tests/test_vote_arch.py` | vote_arch のテスト |
| `tests/test_weighted_scores.py` | weighted_scores のテスト |
| `tests/test_wick_detection.py` | wick_detection のテスト |
| `tests/tests_trade_patterns.py` | tests_trade_patterns のテスト |
| `training/offline_policy_learning.py` | Offline policy learning モジュール |
| `training/train_regime_model.py` | Train regime model モジュール |
