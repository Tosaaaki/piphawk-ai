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
