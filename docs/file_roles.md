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
| `ai/__init__.py` | No description |
| `ai/local_model.py` | OpenAI 互換のローカルモデル呼び出しラッパー |
| `ai/macro_analyzer.py` | FRED と GDELT からニュースを取得して要約するモジュール |
| `ai/policy_trainer.py` | Offline RL trainer for strategy selection. |
| `ai/prompt_templates.py` | プロンプトテンプレート管理モジュール |
| `analysis/__init__.py` | No description |
| `analysis/ai_strategy.py` | AI ストラテジー補助モジュール. |
| `analysis/backtest_utils.py` | Simple backtest helper. |
| `analysis/cluster_regime.py` | No description |
| `analysis/detect_mode.py` | No description |
| `analysis/filter_statistics.py` | フィルター効果を集計する簡易スクリプト. |
| `analysis/llm_mode_selector.py` | No description |
| `analysis/log_analysis.py` | No description |
| `analysis/mode_detector.py` | No description |
| `analysis/mode_preclassifier.py` | No description |
| `analysis/regime_detector.py` | Range からトレンドへの移行を検知するモジュール. |
| `analysis/signal_filter.py` | Multi timeframe alignment checks. |
| `analysis/trade_patterns.py` | Trade pattern scoring utilities. |
| `backend/__init__.py` | No description |
| `backend/analysis/__init__.py` | No description |
| `backend/analysis/param_performance.py` | No description |
| `backend/api/__init__.py` | No description |
| `backend/api/main.py` | No description |
| `backend/api/test_control_endpoints.py` | No description |
| `backend/api/test_panic_stop.py` | No description |
| `backend/api/test_recent_trades.py` | No description |
| `backend/config/__init__.py` | No description |
| `backend/config/defaults.py` | Default configuration values for runtime. |
| `backend/core/__init__.py` | No description |
| `backend/core/ai_throttle.py` | AI call cooldown management. |
| `backend/data/__init__.py` | No description |
| `backend/filters/__init__.py` | General entry filter helpers. |
| `backend/filters/breakout_entry.py` | Breakout entry filter. |
| `backend/filters/extension_block.py` | No description |
| `backend/filters/false_break_filter.py` | False break detection filter. |
| `backend/filters/h1_level_block.py` | H1 support/resistance level block filter. |
| `backend/filters/scalp_entry.py` | スキャルプ用エントリーフィルター. |
| `backend/filters/trend_pullback.py` | Trend pullback entry filter. |
| `backend/filters/volatility_filter.py` | No description |
| `backend/indicators/__init__.py` | No description |
| `backend/indicators/adx.py` | No description |
| `backend/indicators/atr.py` | No description |
| `backend/indicators/calculate_indicators.py` | No description |
| `backend/indicators/candle_features.py` | No description |
| `backend/indicators/ema.py` | No description |
| `backend/indicators/keltner.py` | Simple Keltner Channel implementation. |
| `backend/indicators/macd.py` | No description |
| `backend/indicators/n_wave.py` | No description |
| `backend/indicators/pivot.py` | No description |
| `backend/indicators/polarity.py` | No description |
| `backend/indicators/rolling.py` | Rolling indicator utilities using deque for efficiency. |
| `backend/indicators/rsi.py` | No description |
| `backend/indicators/vwap_band.py` | No description |
| `backend/logs/__init__.py` | No description |
| `backend/logs/cleanup.py` | No description |
| `backend/logs/daily_summary.py` | No description |
| `backend/logs/exit_logger.py` | No description |
| `backend/logs/fetch_oanda_trades.py` | No description |
| `backend/logs/info_logger.py` | No description |
| `backend/logs/initial_fetch_oanda_trades.py` | No description |
| `backend/logs/log_manager.py` | No description |
| `backend/logs/perf_stats_logger.py` | Simple performance logging utility. |
| `backend/logs/reconcile_trades.py` | No description |
| `backend/logs/show_param_history.py` | No description |
| `backend/logs/show_tables.py` | No description |
| `backend/logs/trade_logger.py` | No description |
| `backend/logs/update_oanda_trades.py` | No description |
| `backend/main.py` | No description |
| `backend/market_data/__init__.py` | No description |
| `backend/market_data/candle_fetcher.py` | No description |
| `backend/market_data/tick_fetcher.py` | No description |
| `backend/market_data/tick_metrics.py` | No description |
| `backend/market_data/tick_stream.py` | No description |
| `backend/orders/__init__.py` | No description |
| `backend/orders/mock_order_manager.py` | Paper trading mock order manager. |
| `backend/orders/order_manager.py` | No description |
| `backend/orders/position_manager.py` | No description |
| `backend/reentry_manager.py` | No description |
| `backend/risk_manager.py` | No description |
| `backend/scheduler/__init__.py` | No description |
| `backend/scheduler/job_runner.py` | No description |
| `backend/scheduler/policy_updater.py` | Background updater for offline policy files. |
| `backend/scheduler/strategy_selector.py` | No description |
| `backend/strategy/__init__.py` | No description |
| `backend/strategy/dynamic_pullback.py` | Dynamic pullback threshold calculation. |
| `backend/strategy/entry_ai_decision.py` | DEPRECATED MODULE |
| `backend/strategy/entry_logic.py` | No description |
| `backend/strategy/exit_ai_decision.py` | AI‑based exit decision module. |
| `backend/strategy/exit_logic.py` | No description |
| `backend/strategy/false_break_filter.py` | False breakout detection utilities. |
| `backend/strategy/higher_tf_analysis.py` | higher_tf_analysis.py |
| `backend/strategy/llm_exit.py` | No description |
| `backend/strategy/momentum_follow.py` | ブレイク後のモメンタムを利用した追随エントリー判定用モジュール. |
| `backend/strategy/openai_analysis.py` | OpenAIモデルを用いたトレード分析ユーティリティ |
| `backend/strategy/openai_micro_scalp.py` | No description |
| `backend/strategy/openai_prompt.py` | Prompt generation utilities for OpenAI analysis. |
| `backend/strategy/openai_scalp_analysis.py` | No description |
| `backend/strategy/pattern_ai_detection.py` | No description |
| `backend/strategy/pattern_scanner.py` | No description |
| `backend/strategy/range_break.py` | No description |
| `backend/strategy/reentry_manager.py` | Manage cooldown after stop-loss exits. |
| `backend/strategy/risk_manager.py` | Risk management helper functions. |
| `backend/strategy/selector.py` | RL ポリシーに基づく戦略セレクタ. |
| `backend/strategy/signal_filter.py` | 軽量シグナル・フィルター |
| `backend/strategy/strategy_analyzer.py` | No description |
| `backend/strategy/validators.py` | Helper functions for validating AI trade plans. |
| `backend/tests/__init__.py` | No description |
| `backend/tests/test_adjust_tp_sl.py` | No description |
| `backend/tests/test_adx_bb_score.py` | No description |
| `backend/tests/test_adx_slope_bias.py` | No description |
| `backend/tests/test_ai_cooldown.py` | No description |
| `backend/tests/test_ai_decision_logging.py` | No description |
| `backend/tests/test_ai_throttle.py` | No description |
| `backend/tests/test_align_adx_weight.py` | No description |
| `backend/tests/test_align_bypass.py` | No description |
| `backend/tests/test_atr_boost_detector.py` | No description |
| `backend/tests/test_atr_breakout.py` | No description |
| `backend/tests/test_atr_tp_sl_mult.py` | No description |
| `backend/tests/test_be_volatility_sl.py` | No description |
| `backend/tests/test_breakout_entry.py` | No description |
| `backend/tests/test_candle_fetcher.py` | No description |
| `backend/tests/test_candle_summary.py` | No description |
| `backend/tests/test_climax_detection.py` | No description |
| `backend/tests/test_composite_threshold.py` | No description |
| `backend/tests/test_consecutive_high_low.py` | No description |
| `backend/tests/test_consistency_normalization.py` | No description |
| `backend/tests/test_consistency_weights.py` | No description |
| `backend/tests/test_cooldown_refresh.py` | No description |
| `backend/tests/test_counter_trend_block.py` | No description |
| `backend/tests/test_duplicate_entry_prevention.py` | No description |
| `backend/tests/test_dynamic_pullback.py` | No description |
| `backend/tests/test_dynamic_sl.py` | No description |
| `backend/tests/test_early_exit_threshold.py` | No description |
| `backend/tests/test_entry_break_override.py` | No description |
| `backend/tests/test_entry_confidence.py` | No description |
| `backend/tests/test_entry_cost_guard.py` | No description |
| `backend/tests/test_entry_decline_cancel.py` | No description |
| `backend/tests/test_entry_filter_rsi.py` | No description |
| `backend/tests/test_entry_regime_logging.py` | No description |
| `backend/tests/test_entry_skip_logging.py` | No description |
| `backend/tests/test_env_loader.py` | No description |
| `backend/tests/test_exit_bias_factor.py` | No description |
| `backend/tests/test_exit_cooldown.py` | No description |
| `backend/tests/test_exit_logic_high_atr_low_adx.py` | No description |
| `backend/tests/test_exit_pattern_override.py` | No description |
| `backend/tests/test_exit_pips_symmetry.py` | No description |
| `backend/tests/test_exit_reason_logging.py` | No description |
| `backend/tests/test_exit_serialization.py` | No description |
| `backend/tests/test_exit_trade_market_close.py` | No description |
| `backend/tests/test_extension_block.py` | No description |
| `backend/tests/test_fallback_dynamic_risk.py` | No description |
| `backend/tests/test_false_break_filter.py` | No description |
| `backend/tests/test_follow_breakout_call.py` | No description |
| `backend/tests/test_follow_through.py` | No description |
| `backend/tests/test_h1_level_block.py` | No description |
| `backend/tests/test_higher_tf_override.py` | No description |
| `backend/tests/test_higher_tf_pivot.py` | No description |
| `backend/tests/test_higher_tf_prompt.py` | No description |
| `backend/tests/test_higher_tf_tp.py` | No description |
| `backend/tests/test_job_runner_env_mode.py` | No description |
| `backend/tests/test_job_runner_handles_none_indicators.py` | No description |
| `backend/tests/test_job_runner_restore_mode.py` | No description |
| `backend/tests/test_job_runner_tp_flags.py` | No description |
| `backend/tests/test_keltner.py` | No description |
| `backend/tests/test_limit_retry.py` | No description |
| `backend/tests/test_llm_exit_adjustment.py` | No description |
| `backend/tests/test_lower_tf_weight.py` | No description |
| `backend/tests/test_macd.py` | No description |
| `backend/tests/test_market_condition_break.py` | No description |
| `backend/tests/test_market_condition_cooldown.py` | No description |
| `backend/tests/test_market_condition_fallback.py` | No description |
| `backend/tests/test_market_condition_override.py` | No description |
| `backend/tests/test_market_di_cross_float.py` | No description |
| `backend/tests/test_min_hold_exit.py` | No description |
| `backend/tests/test_n_wave.py` | No description |
| `backend/tests/test_no_pullback_prompt.py` | No description |
| `backend/tests/test_noise_prompt.py` | No description |
| `backend/tests/test_openai_cache_limit.py` | No description |
| `backend/tests/test_partial_close.py` | No description |
| `backend/tests/test_pattern_ai_detection.py` | No description |
| `backend/tests/test_pattern_detection.py` | No description |
| `backend/tests/test_pattern_prompt.py` | No description |
| `backend/tests/test_pattern_scanner.py` | No description |
| `backend/tests/test_peak_entry.py` | No description |
| `backend/tests/test_pivot_calc.py` | No description |
| `backend/tests/test_pivot_suppression.py` | No description |
| `backend/tests/test_polarity_exit.py` | No description |
| `backend/tests/test_price_format.py` | No description |
| `backend/tests/test_price_formatting.py` | No description |
| `backend/tests/test_prob_validation.py` | No description |
| `backend/tests/test_prompt_bias.py` | No description |
| `backend/tests/test_prompt_m15.py` | No description |
| `backend/tests/test_pullback_bypass.py` | No description |
| `backend/tests/test_pullback_limit.py` | No description |
| `backend/tests/test_pullback_prompt.py` | No description |
| `backend/tests/test_range_break_alert.py` | No description |
| `backend/tests/test_range_break_detection.py` | No description |
| `backend/tests/test_range_index_series.py` | No description |
| `backend/tests/test_rapid_reversal_block.py` | No description |
| `backend/tests/test_recent_candle_bias.py` | No description |
| `backend/tests/test_reconcile_trades.py` | No description |
| `backend/tests/test_reentry_manager.py` | No description |
| `backend/tests/test_regime_breakout_entry_method.py` | No description |
| `backend/tests/test_regime_caching.py` | No description |
| `backend/tests/test_regime_cross_delay.py` | No description |
| `backend/tests/test_regime_detector.py` | No description |
| `backend/tests/test_regime_filters.py` | No description |
| `backend/tests/test_regime_override.py` | No description |
| `backend/tests/test_reversal_exit.py` | No description |
| `backend/tests/test_risk_expected_value.py` | No description |
| `backend/tests/test_risk_manager.py` | No description |
| `backend/tests/test_rrr_enforcement.py` | No description |
| `backend/tests/test_scale_constraints.py` | No description |
| `backend/tests/test_scale_entry.py` | No description |
| `backend/tests/test_scalp_cond_tf.py` | No description |
| `backend/tests/test_scalp_mode.py` | No description |
| `backend/tests/test_short_sl_price.py` | No description |
| `backend/tests/test_signal_manager.py` | No description |
| `backend/tests/test_signal_manager_breakout.py` | No description |
| `backend/tests/test_spread_check.py` | No description |
| `backend/tests/test_tf_weight_normalization.py` | No description |
| `backend/tests/test_tp_bb_ratio.py` | No description |
| `backend/tests/test_tp_extension.py` | No description |
| `backend/tests/test_tp_ratio.py` | No description |
| `backend/tests/test_tp_reduction.py` | No description |
| `backend/tests/test_trade_plan_parse_error.py` | No description |
| `backend/tests/test_trailing_calendar.py` | No description |
| `backend/tests/test_trailing_stop_abs.py` | No description |
| `backend/tests/test_trend_pullback.py` | No description |
| `backend/tests/test_update_trade_sl.py` | No description |
| `backend/tests/test_volatility_filter.py` | No description |
| `backend/tests/test_vwap_band.py` | No description |
| `backend/tests/test_weight_last.py` | No description |
| `backend/utils/__init__.py` | No description |
| `backend/utils/ai_parse.py` | No description |
| `backend/utils/async_helper.py` | No description |
| `backend/utils/db_helper.py` | No description |
| `backend/utils/env_loader.py` | No description |
| `backend/utils/http_client.py` | No description |
| `backend/utils/notification.py` | Utility module for outbound LINE notifications. |
| `backend/utils/oanda_client.py` | OANDA helper – pending LIMIT order lookup |
| `backend/utils/openai_client.py` | Thin wrapper around the OpenAI client with optional lazy import. |
| `backend/utils/price.py` | Utility helpers for price formatting / rounding before sending orders |
| `backend/utils/prompt_loader.py` | Prompt template loader utility. |
| `backend/utils/restart_guard.py` | Restart guard to prevent excessive self-restarts. |
| `backend/utils/trade_time.py` | No description |
| `benchmarks/bench_tick_pipeline.py` | 簡易ティックパイプラインベンチマーク. |
| `config/__init__.py` | No description |
| `config/params_loader.py` | Load parameters from params.yaml and strategy.yml into environment variables. |
| `core/__init__.py` | コアユーティリティをまとめたモジュール. |
| `core/ring_buffer.py` | No description |
| `diagnostics/__init__.py` | No description |
| `diagnostics/diagnostics.py` | No description |
| `diagnostics/view_logs.py` | No description |
| `execution/__init__.py` | No description |
| `execution/scalp_manager.py` | Scalp trade management. |
| `execution/sync_manager.py` | No description |
| `fast_metrics.py` | No description |
| `indicators/__init__.py` | Indicator helpers for trading signals. |
| `indicators/bollinger.py` | No description |
| `indicators/candlestick.py` | No description |
| `indicators/patterns.py` | No description |
| `indicators/volatility.py` | No description |
| `maintenance/__init__.py` | No description |
| `maintenance/disk_guard.py` | Call this from your main loop (or run standalone). |
| `maintenance/system_cleanup.py` | System maintenance script |
| `monitoring/__init__.py` | 監視機能を提供するサブモジュール. |
| `monitoring/metrics_publisher.py` | Kafka と Prometheus へメトリクスを送信するユーティリティ. |
| `monitoring/safety_trigger.py` | 損失やエラー発生数を監視して安全停止を行うためのモジュール. |
| `pipelines/walk_forward/eval_kpi.py` | Evaluate KPI and decide retrain flag. |
| `pipelines/walk_forward/run_walk_forward.py` | Walk-forward optimization main script. |
| `pipelines/walk_forward/utils.py` | No description |
| `piphawk_ai/__init__.py` | Namespace package for piphawk AI. |
| `piphawk_ai/main.py` | No description |
| `piphawk_ai/policy/offline.py` | No description |
| `piphawk_ai/risk/cvar.py` | Wrapper for CVaR calculation utilities. |
| `piphawk_ai/risk/manager.py` | CVaR-based portfolio risk management. |
| `piphawk_ai/runner/__init__.py` | Runner package. |
| `piphawk_ai/runner/core.py` | No description |
| `piphawk_ai/runner/entry.py` | Entry-related helpers for JobRunner. |
| `piphawk_ai/runner/exit.py` | Exit-related helpers for JobRunner. |
| `piphawk_ai/tech_arch/__init__.py` | Technical entry pipeline package. |
| `piphawk_ai/tech_arch/ai_decision.py` | No description |
| `piphawk_ai/tech_arch/entry_gate.py` | No description |
| `piphawk_ai/tech_arch/indicator_engine.py` | No description |
| `piphawk_ai/tech_arch/m5_entry.py` | No description |
| `piphawk_ai/tech_arch/market_classifier.py` | No description |
| `piphawk_ai/tech_arch/market_context.py` | No description |
| `piphawk_ai/tech_arch/mode_detector.py` | No description |
| `piphawk_ai/tech_arch/pipeline.py` | No description |
| `piphawk_ai/tech_arch/post_filters.py` | No description |
| `piphawk_ai/tech_arch/prefilters.py` | No description |
| `piphawk_ai/tech_arch/risk_filters.py` | No description |
| `piphawk_ai/tech_arch/rule_validator.py` | No description |
| `piphawk_ai/vote_arch/__init__.py` | Majority-vote trading pipeline components. |
| `piphawk_ai/vote_arch/ai_entry_plan.py` | Deterministic entry plan generation via OpenAI. |
| `piphawk_ai/vote_arch/ai_strategy_selector.py` | Select trade strategy via OpenAI and majority vote. |
| `piphawk_ai/vote_arch/entry_buffer.py` | Simple vertical ensemble buffer for entry plans. |
| `piphawk_ai/vote_arch/market_air_sensor.py` | Calculate market air index used in prompts. |
| `piphawk_ai/vote_arch/pipeline.py` | No description |
| `piphawk_ai/vote_arch/post_filters.py` | Final safety checks for entry plans. |
| `piphawk_ai/vote_arch/regime_detector.py` | Simple rule-based regime detection. |
| `piphawk_ai/vote_arch/trade_mode_selector.py` | Select final trade mode with rule fallback. |
| `regime/__init__.py` | No description |
| `regime/features.py` | No description |
| `regime/gmm_detector.py` | No description |
| `regime/hdbscan_detector.py` | No description |
| `risk/__init__.py` | No description |
| `risk/cvar.py` | No description |
| `risk/manager.py` | CVaR-based portfolio risk management. |
| `risk/portfolio_risk_manager.py` | Backward compatibility for PortfolioRiskManager import. |
| `risk/tp_sl_manager.py` | TP/SL ratio adjustment utilities. |
| `risk/trade_guard.py` | Simple losing streak guard. |
| `selector_fast.py` | Entry rule selector with LinUCB. |
| `signals/__init__.py` | No description |
| `signals/adx_strategy.py` | No description |
| `signals/composite_mode.py` | No description |
| `signals/mode_params.py` | No description |
| `signals/regime_filter.py` | Regime conflict blocker. |
| `signals/scalp_momentum.py` | No description |
| `signals/scalp_strategy.py` | No description |
| `signals/signal_manager.py` | シグナル管理モジュール. |
| `signals/trend_filter.py` | Multi timeframe EMA trend filter. |
| `strategies/__init__.py` | Strategy modules. |
| `strategies/bandit_manager.py` | Bandit based strategy manager. |
| `strategies/base.py` | Strategy base classes. |
| `strategies/context_builder.py` | No description |
| `strategies/scalp/entry_rules.py` | Scalp entry rules. |
| `strategies/scalp_strategy.py` | Simple scalp strategy wrapper. |
| `strategies/selector.py` | Backward compatibility wrapper for StrategySelector. |
| `strategies/trend_strategy.py` | Simple trend-follow strategy wrapper. |
| `tests/conftest.py` | No description |
| `tests/test_adx_mode.py` | No description |
| `tests/test_bollinger_regression.py` | No description |
| `tests/test_composite_scoring.py` | No description |
| `tests/test_cvar.py` | No description |
| `tests/test_double_bottom_signal.py` | No description |
| `tests/test_double_top_signal.py` | No description |
| `tests/test_entry_logic.py` | No description |
| `tests/test_entry_rules.py` | No description |
| `tests/test_fast_metrics.py` | No description |
| `tests/test_force_close.py` | No description |
| `tests/test_forced_entry_bypass.py` | No description |
| `tests/test_format_price.py` | No description |
| `tests/test_gmm_detector.py` | No description |
| `tests/test_hdbscan_detector.py` | No description |
| `tests/test_indicators_extra.py` | No description |
| `tests/test_job_runner_tech_pipeline.py` | No description |
| `tests/test_job_runner_vote_arch.py` | No description |
| `tests/test_log_analysis.py` | No description |
| `tests/test_metrics_publisher_basic.py` | No description |
| `tests/test_micro_scalp.py` | No description |
| `tests/test_mode_detector_cfg.py` | No description |
| `tests/test_mode_selector.py` | No description |
| `tests/test_overshoot_dynamic.py` | No description |
| `tests/test_overshoot_window.py` | No description |
| `tests/test_params_loader_mode.py` | No description |
| `tests/test_params_loader_scalp.py` | No description |
| `tests/test_params_loader_strategy.py` | No description |
| `tests/test_pipeline.py` | No description |
| `tests/test_portfolio_risk_manager.py` | No description |
| `tests/test_process_entry_return.py` | No description |
| `tests/test_prompt_log.py` | No description |
| `tests/test_range_adx_count.py` | No description |
| `tests/test_ring_buffer.py` | No description |
| `tests/test_rule_selector.py` | No description |
| `tests/test_safety_trigger.py` | No description |
| `tests/test_safety_trigger_basic.py` | No description |
| `tests/test_scalp_manager.py` | No description |
| `tests/test_scalp_manager_dynamic_tp.py` | No description |
| `tests/test_scalp_manager_hold.py` | No description |
| `tests/test_scalp_momentum_exit.py` | No description |
| `tests/test_scalp_strategy.py` | No description |
| `tests/test_scalp_trailing_after_tp.py` | No description |
| `tests/test_strategy_selector.py` | No description |
| `tests/test_strategy_selector_dynamic.py` | No description |
| `tests/test_strategy_selector_offline.py` | No description |
| `tests/test_sync_manager.py` | No description |
| `tests/test_tech_arch_flow.py` | No description |
| `tests/test_tech_arch_no_ai.py` | No description |
| `tests/test_trend_adx_thresh.py` | No description |
| `tests/test_trend_strategy.py` | No description |
| `tests/test_update_oanda_trades_logs.py` | No description |
| `tests/test_validators.py` | No description |
| `tests/test_volume_ratio.py` | No description |
| `tests/test_vote_arch.py` | No description |
| `tests/test_weighted_scores.py` | No description |
| `tests/test_wick_detection.py` | No description |
| `tests/tests_trade_patterns.py` | No description |
| `training/offline_policy_learning.py` | No description |
| `training/train_regime_model.py` | No description |
