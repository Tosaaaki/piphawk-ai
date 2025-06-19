# ファイルの役割

リポジトリ直下にある主要ファイルとディレクトリの役割を日本語でまとめています。
目的や利用シーンがひと目で分かるよう、簡潔な説明を添えました。

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
| `analysis/strategy_utils.py` | AI による取引戦略のエントリーポイント |
| `backend/api/main.py` | FastAPI サーバーの起動スクリプト |
| `execution/scalp_manager.py` | スキャルピング実行の管理処理 |
| `piphawk_ai/main.py` | ジョブランナー全体を起動するメイン処理 |
| `piphawk_ai/runner/entry.py` | 各戦略のエントリー判断ロジック |
| `core/ring_buffer.py` | ティックデータを保持するリングバッファ実装 |

## Python ファイル一覧

以下はリポジトリに含まれる Python ファイルと、それぞれの簡単な説明です。

| パス | 説明 |
| --- | --- |
| `ai/__init__.py` | パッケージ初期化ファイル |
| `ai/local_model.py` | OpenAI 互換のローカルモデル呼び出しラッパー |
| `ai/macro_analyzer.py` | FRED と GDELT からニュースを取得して要約するモジュール |
| `ai/policy_trainer.py` | 戦略選択のためのオフラインRLトレーナー。 |
| `ai/prompt_templates.py` | プロンプトテンプレート管理モジュール |
| `analysis/__init__.py` | trade_patterns からスコア計算関数 |
| `analysis/strategy_utils.py` | AI ストラテジー補助モジュール. |
| `analysis/backtest_utils.py` | 単純なバックテストヘルパー。 |
| `analysis/cluster_regime.py` | 学習済みクラスタリングモデルを用いたレジーム推定ヘルパー. |
| `analysis/detect_mode.py` | ローカルトレードモード検出ユーティリティ。 |
| `analysis/filter_statistics.py` | フィルター効果を集計する簡易スクリプト. |
| `analysis/llm_mode_selector.py` | LLM を用いたモード選択ラッパー. |
| `analysis/log_analysis.py` | ログ分析のためのユーティリティ機能。 |
| `analysis/mode_detector.py` | LLMなしの単純なトレードモード検出器。 |
| `analysis/mode_preclassifier.py` | 単純なADX/ATRベースの取引レジーム判定モジュール. |
| `analysis/regime_detector.py` | Range からトレンドへの移行を検知するモジュール. |
| `analysis/signal_filter.py` | マルチフレームアライメントチェック。 |
| `analysis/trade_patterns.py` | トレードパターンスコアリングユーティリティ。 |
| `backend/__init__.py` | プロジェクトルートを PYTHONPATH に追加 |
| `backend/analysis/__init__.py` | パッケージ初期化ファイル |
| `backend/analysis/param_performance.py` | パラメーター変更パフォーマンス分析。 |
| `backend/api/__init__.py` | パッケージ初期化ファイル |
| `backend/api/main.py` | 小さなJSONペイロードで200 OKを返します。 |
| `backend/api/test_control_endpoints.py` | control_endpoints のテスト |
| `backend/api/test_panic_stop.py` | panic_stop のテスト |
| `backend/api/test_recent_trades.py` | recent_trades のテスト |
| `backend/config/__init__.py` | パッケージ初期化ファイル |
| `backend/config/defaults.py` | ランタイムのデフォルト構成値。 |
| `backend/core/__init__.py` | パッケージ初期化ファイル |
| `backend/core/ai_throttle.py` | AIコールクールダウン管理。 |
| `backend/data/__init__.py` | パッケージ初期化ファイル |
| `backend/filters/__init__.py` | 一般的なエントリフィルターヘルパー。 |
| `backend/filters/breakout_entry.py` | ブレイクアウトエントリフィルター。 |
| `backend/filters/extension_block.py` | 価格がEMAから遠く離れて延長されたら、エントリを防止します。 |
| `backend/filters/false_break_filter.py` | 誤った破損検出フィルター。 |
| `backend/filters/h1_level_block.py` | H1サポート/抵抗レベルブロックフィルター。 |
| `backend/filters/scalp_entry.py` | スキャルプ用エントリーフィルター. |
| `backend/filters/trend_pullback.py` | トレンドプルバックエントリフィルター。 |
| `backend/filters/volatility_filter.py` | ボラティリティとブレイクアウトフィルター。 |
| `backend/indicators/__init__.py` | パッケージ初期化ファイル |
| `backend/indicators/adx.py` | 平均的な方向ムーブメントインデックス（ADX）実装。 |
| `backend/indicators/atr.py` | 指定された価格データの平均真範囲（ATR）を計算します。 |
| `backend/indicators/calculate_indicators.py` | 「シリーズ」（0-100）内で「値」のパーセンタイルランクを返します。 |
| `backend/indicators/candle_features.py` | ボリュームの単純な移動平均を返します。 |
| `backend/indicators/ema.py` | 特定のリストまたは一連の価格の指数移動平均（EMA）を計算します。 |
| `backend/indicators/keltner.py` | シンプルなケルトナーチャネルの実装。 |
| `backend/indicators/macd.py` | MACDラインと信号ラインを返します。 |
| `backend/indicators/n_wave.py` | 検出可能な場合、投影されたN-Wave目標価格を返します。 |
| `backend/indicators/pivot.py` | クラシックフロアトレーダーピボットレベルを返します。 |
| `backend/indicators/polarity.py` | -1から1の間のローリング極性スコアを返します。 |
| `backend/indicators/rolling.py` | 効率のためにDequeを使用したローリングインジケーターユーティリティ。 |
| `backend/indicators/rsi.py` | Rsi モジュール |
| `backend/indicators/vwap_band.py` | 指定された価格とボリュームシリーズのVWAPを返します。 |
| `backend/logs/__init__.py` | パッケージ初期化ファイル |
| `backend/logs/cleanup.py` | データベースをVACUUMして不要領域を解放する |
| `backend/logs/daily_summary.py` | Instrument、close_price、tp_price、units、close_timeを選択します |
| `backend/logs/exit_logger.py` | exit_log.jsonlにJSONデータを追加します |
| `backend/logs/fetch_oanda_trades.py` | Env_loaderは、インポート時にデフォルトのenvファイルを自動的にロードします |
| `backend/logs/info_logger.py` | ログフォーマットされた情報メッセージ。 |
| `backend/logs/initial_fetch_oanda_trades.py` | oanda_tradesを更新します |
| `backend/logs/log_manager.py` | 現在のデータベースパスを返します。 |
| `backend/logs/perf_stats_logger.py` | シンプルなパフォーマンスロギングユーティリティ。 |
| `backend/logs/reconcile_trades.py` | ISO文字列をUTC DateTimeを認識して変換します。 |
| `backend/logs/show_param_history.py` | param_changes テーブルから履歴を取得する |
| `backend/logs/show_tables.py` | テーブル名の返品リスト。 |
| `backend/logs/trade_logger.py` | `` exitreason``の列挙とRLロギングを許可するlog_tradeのラッパー。 |
| `backend/logs/update_oanda_trades.py` | データベース操作は、データベースがロックされているときに操作を操作します。 |
| `backend/main.py` | Piphawkコンポーネントを実行するための便利なエントリポイント。 |
| `backend/market_data/__init__.py` | パッケージ初期化ファイル |
| `backend/market_data/candle_fetcher.py` | Oanda APIからCandlestickデータを取得します。 |
| `backend/market_data/tick_fetcher.py` | Oanda APIから最新のティック（価格）データを取得します。 |
| `backend/market_data/tick_metrics.py` | ダニベースのメトリック計算。 |
| `backend/market_data/tick_stream.py` | HTTP Long Pollingを介したOandaストリーミングクライアント。 |
| `backend/orders/__init__.py` | オーダーマネージャーファクトリー。 |
| `backend/orders/mock_order_manager.py` | 紙取引模擬注文マネージャー。 |
| `backend/orders/order_manager.py` | requests.responseからエラーコードと誤差を抽出します。 |
| `backend/orders/position_manager.py` | アカウントの概要からマージュされた電流を返します。 |
| `backend/reentry_manager.py` | SL直後の再エントリー判定を行うヘルパー。 |
| `backend/risk_manager.py` | ATRとの比較に基づきSLが適切か検証する。 |
| `backend/scheduler/__init__.py` | パッケージ初期化ファイル |
| `backend/scheduler/job_runner.py` | use_vote_pipelineに基づいて選択したパイプラインを実行します。 |
| `backend/scheduler/policy_updater.py` | オフラインポリシーファイルのバックグラウンドアップデーター。 |
| `backend/scheduler/strategy_selector.py` | オプションのオフラインポリシーを備えたLINUCBを使用した戦略選択。 |
| `backend/strategy/__init__.py` | パッケージ初期化ファイル |
| `backend/strategy/dynamic_pullback.py` | 動的プルバックしきい値計算。 |
| `backend/strategy/entry_ai_decision.py` | 非推奨モジュール |
| `backend/strategy/entry_logic.py` | プルバックの方向にある指定されたPIPSによってオフセットされたリミット価格の価格を返します。 |
| `backend/strategy/exit_ai_decision.py` | AIベースの出口決定モジュール。 |
| `backend/strategy/exit_logic.py` | AI分析の現在の位置、市場データ、および指標を説明するプロンプトを生成します。 |
| `backend/strategy/false_break_filter.py` | 誤ったブレイクアウト検出ユーティリティ。 |
| `backend/strategy/higher_tf_analysis.py` | higher_tf_analysis.py  |
| `backend/strategy/llm_exit.py` | AI駆動型の出口調整ヘルパー。 |
| `backend/strategy/momentum_follow.py` | ブレイク後のモメンタムを利用した追随エントリー判定用モジュール. |
| `backend/strategy/openai_analysis.py` | OpenAIモデルを用いたトレード分析ユーティリティ |
| `backend/strategy/openai_micro_scalp.py` | Micro-Scalp分析のためにプロンプ​​トテキストを返します。 |
| `backend/strategy/openai_prompt.py` | OpenAI分析のための迅速な生成ユーティリティ。 |
| `backend/strategy/openai_scalp_analysis.py` | パンダシリーズまたはリストから最後の「n``値を返します。 |
| `backend/strategy/pattern_ai_detection.py` | OpenAIを使用してチャートパターンを検出します。 |
| `backend/strategy/pattern_scanner.py` | キャンドルデータをOHLC辞書の標準リストに変換します。 |
| `backend/strategy/range_break.py` | 最新のろうそくが最近の範囲外で閉鎖されているかどうかを検出します。 |
| `backend/strategy/reentry_manager.py` | ストップロスの出口後にクールダウンを管理します。 |
| `backend/strategy/risk_manager.py` | リスク管理ヘルパー機能。 |
| `backend/strategy/selector.py` | RL ポリシーに基づく戦略セレクタ. |
| `backend/strategy/signal_filter.py` | 軽量シグナル・フィルター |
| `backend/strategy/strategy_analyzer.py` | .envファイルから戦略パラメータを読み込む |
| `backend/strategy/validators.py` | ヘルパーは、AI貿易計画を検証するために機能します。 |
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
| `backend/utils/ai_parse.py` | DICTまたはJSON文字列である可能性のあるOpenaiの回答を安全に解析します。 |
| `backend/utils/async_helper.py` | 非同期関数を同期的に実行するユーティリティ |
| `backend/utils/db_helper.py` | シンプルなSQLiteヘルパーユーティリティ。 |
| `backend/utils/env_loader.py` | 環境変数管理のユーティリティ関数。 |
| `backend/utils/http_client.py` | HTTPリクエストをリトライ付きで実行するユーティリティ |
| `backend/utils/notification.py` | アウトバウンドライン通知のユーティリティモジュール。 |
| `backend/utils/oanda_client.py` | Panda Helper  - 保留中の制限注文検索 |
| `backend/utils/openai_client.py` | オプションの怠zyなインポートを使用して、Openaiクライアントの周りの薄いラッパー。 |
| `backend/utils/price.py` | 注文を送信する前に、価格のフォーマット /丸めのためのユーティリティヘルパー |
| `backend/utils/prompt_loader.py` | プロンプトテンプレートローダーユーティリティ。 |
| `backend/utils/restart_guard.py` | 過度の自己評価を防ぐためにガードを再起動します。 |
| `backend/utils/trade_time.py` | 貿易タイムスタンプのユーティリティヘルパー。 |
| `config/__init__.py` | 構成のパッケージ初期化 |
| `config/params_loader.py` | Params.yamlおよびStrategy.ymlから環境変数へのロードパラメーター。 |
| `core/__init__.py` | コアユーティリティをまとめたモジュール. |
| `core/ring_buffer.py` | 固定長リングバッファ. |
| `diagnostics/__init__.py` | パッケージ初期化ファイル |
| `diagnostics/diagnostics.py` | 存在しない場合はテーブルを作成します（診断） |
| `diagnostics/view_logs.py` | View logs モジュール |
| `execution/__init__.py` | パッケージ初期化ファイル |
| `execution/scalp_manager.py` | 頭皮貿易管理。 |
| `execution/sync_manager.py` | Oandaの歴史を使用して、取引出口を更新します。 |
| `fast_metrics.py` | 軽量な指標計算モジュール. |
| `indicators/__init__.py` | 取引信号のインジケータヘルパー。 |
| `indicators/bollinger.py` | 複数の時間軸に対応したボリンジャーバンドのユーティリティ。 |
| `indicators/candlestick.py` | ろうそくの上部影の比率を返します。 |
| `indicators/patterns.py` | 二重底パターンとコンピューティング機能を検出します。 |
| `indicators/volatility.py` | ボラティリティ測定のためのユーティリティ関数。 |
| `maintenance/__init__.py` | メンテナンスのためのパッケージの初期化 |
| `maintenance/disk_guard.py` | メインループ（またはスタンドアロンを実行）からこれを呼び出します。 |
| `maintenance/system_cleanup.py` | システムメンテナンススクリプト |
| `monitoring/__init__.py` | 監視機能を提供するサブモジュール. |
| `monitoring/metrics_publisher.py` | Kafka と Prometheus へメトリクスを送信するユーティリティ. |
| `monitoring/safety_trigger.py` | 損失やエラー発生数を監視して安全停止を行うためのモジュール. |
| `monitoring/prom_exporter.py` | Prometheus メトリクスを `/metrics` で公開するエクスポーター. |
| `monitoring/grafana_import.py` | Grafana ダッシュボードを自動インポートするスクリプト. |
| `pipelines/walk_forward/eval_kpi.py` | kpiを評価し、再lainフラグを決定します。 |
| `pipelines/walk_forward/run_walk_forward.py` | ウォークフォワード最適化メインスクリプト。 |
| `pipelines/walk_forward/utils.py` | 単純なウォークフォワード取引のためのユーティリティ機能。 |
| `piphawk_ai/__init__.py` | Piphawk AIの名前空間パッケージ。 |
| `piphawk_ai/main.py` | Main モジュール |
| `piphawk_ai/policy/offline.py` | オフライン強化学習ポリシーローダー。 |
| `piphawk_ai/risk/cvar.py` | CVAR計算ユーティリティのラッパー。 |
| `piphawk_ai/risk/manager.py` | CVARベースのポートフォリオリスク管理。 |
| `piphawk_ai/runner/__init__.py` | ランナーパッケージ。 |
| `piphawk_ai/runner/core.py` | AI出口評価のために最小限のコンテキストDICTを作成します。 |
| `piphawk_ai/runner/entry.py` | Jobrunnerのエントリー関連ヘルパー。 |
| `piphawk_ai/runner/exit.py` | Jobrunnerの出口関連ヘルパー。 |
| `piphawk_ai/tech_arch/__init__.py` | 技術的なエントリーパイプラインパッケージ。 |
| `piphawk_ai/tech_arch/ai_decision.py` | M5パイプラインのOpenAI決定ヘルパー。 |
| `piphawk_ai/tech_arch/entry_gate.py` | 技術パイプラインのLLMエントリゲート。 |
| `piphawk_ai/tech_arch/indicator_engine.py` | インジケータ計算ヘルパー。 |
| `piphawk_ai/tech_arch/m5_entry.py` | M5信号検出ヘルパー。 |
| `piphawk_ai/tech_arch/market_classifier.py` | シンプルな市場分類ユーティリティ。 |
| `piphawk_ai/tech_arch/market_context.py` | 技術パイプラインのマーケットスナップショットユーティリティ。 |
| `piphawk_ai/tech_arch/mode_detector.py` | テクニカルパイプラインのdetect_mode周辺のラッパー。 |
| `piphawk_ai/tech_arch/pipeline.py` | M5テクニカルエントリパイプラインオーケストレーター。 |
| `piphawk_ai/tech_arch/post_filters.py` | 技術パイプラインの最終的な安全チェック。 |
| `piphawk_ai/tech_arch/prefilters.py` | テクニカルパイプライン用のプレフィルターユーティリティ。 |
| `piphawk_ai/tech_arch/risk_filters.py` | 技術パイプラインの基本的なリスクフィルター。 |
| `piphawk_ai/tech_arch/rule_validator.py` | エントリープランのシンプルなルールバリデーター。 |
| `piphawk_ai/vote_arch/__init__.py` | 多数票の取引パイプラインコンポーネント。 |
| `piphawk_ai/vote_arch/ai_entry_plan.py` | OpenAI経由の決定論的エントリプランの生成。 |
| `piphawk_ai/vote_arch/ai_strategy_selector.py` | Openaiおよび多数決を介して貿易戦略を選択します。 |
| `piphawk_ai/vote_arch/entry_buffer.py` | エントリープラン用のシンプルな垂直アンサンブルバッファー。 |
| `analysis/atmosphere/market_air_sensor.py` | プロンプトで使用される市場空気インデックスを計算します。 |
| `piphawk_ai/vote_arch/pipeline.py` | 過半数の投票取引アーキテクチャのオーケストレーションパイプライン。 |
| `piphawk_ai/vote_arch/post_filters.py` | エントリープランの最終的な安全チェック。 |
| `piphawk_ai/vote_arch/regime_detector.py` | 単純なルールベースの体制検出。 |
| `piphawk_ai/vote_arch/trade_mode_selector.py` | ルールフォールバックで最終取引モードを選択します。 |
| `regime/__init__.py` | パッケージ初期化ファイル |
| `regime/features.py` | レジーム分類用の特徴量計算ヘルパー. |
| `regime/gmm_detector.py` | Gaussian Mixture Model によるレジーム認識クラス. |
| `regime/hdbscan_detector.py` | HDBSCAN によるレジーム認識クラス. |
| `risk/__init__.py` | パッケージ初期化ファイル |
| `risk/cvar.py` | CVaR (Expected Shortfall) 計算ユーティリティ. |
| `risk/manager.py` | CVARベースのポートフォリオリスク管理。 |
| `risk/portfolio_risk_manager.py` | PortfolioriskManagerのインポートの後方互換性。 |
| `risk/tp_sl_manager.py` | TP/SL比調整ユーティリティ。 |
| `risk/trade_guard.py` | シンプルな負けストリークガード。 |
| `selector_fast.py` | Linucbを使用したエントリルールセレクター。 |
| `signals/__init__.py` | パッケージ初期化ファイル |
| `signals/adx_strategy.py` | ADX値に基づくシンプルなストラテジー切換ユーティリティ. |
| `signals/composite_mode.py` | 複合トレードモードの決定ユーティリティ。 |
| `signals/mode_params.py` | weights項目があれば合計1となるよう正規化する |
| `signals/regime_filter.py` | レジーム紛争ブロッカー。 |
| `signals/scalp_momentum.py` | 頭皮の運動量ユーティリティ。 |
| `signals/scalp_strategy.py` | シンプルなマルチフレームスクラップユーティリティ。 |
| `signals/signal_manager.py` | シグナル管理モジュール. |
| `signals/trend_filter.py` | マルチフレームEMAトレンドフィルター。 |
| `strategies/__init__.py` | 戦略モジュール。 |
| `strategies/bandit_manager.py` | Banditベースの戦略マネージャー。 |
| `strategies/base.py` | 戦略ベースクラス。 |
| `strategies/context_builder.py` | ユーティリティは、戦略選択のためのコンテキストベクトルを構築するための機能を使用します。 |
| `strategies/scalp/entry_rules.py` | 頭皮の入力ルール。 |
| `strategies/scalp_strategy.py` | シンプルな頭皮戦略ラッパー。 |
| `strategies/selector.py` | StrategySelectorの後方互換性ラッパー。 |
| `strategies/trend_strategy.py` | シンプルなトレンドフォロー戦略ラッパー。 |
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
| `training/offline_policy_learning.py` | オフラインポリシー学習モジュール |
| `training/train_regime_model.py` | レジームモデルを学習するモジュール |
