# AGENTS.md

## 1. プロジェクト概要（Project Overview）

### プロジェクトの目的・機能概要

本プロジェクトは、為替自動取引システム（FX Auto-Trading System）であり、為替市場データの取得、指標計算、AI（OpenAI API）を用いた取引判断、および実際の発注（OANDA APIを利用）を行います。

主な機能：

- OANDA API経由でのティックおよびローソク足データ取得
- RSI、ATR、EMA、ボリンジャーバンドなどのテクニカル指標計算
- OpenAI APIを用いたトレンド判断およびエントリー・エグジットの自動判定
- FastAPIバックエンドとReactフロントエンドを使用した管理画面

### 使用技術・フレームワーク

- Python 3.11以上
- FastAPI（APIサーバー）
- React（フロントエンド）
- SQLite（取引ログ）
- OANDA API（市場データ・取引）
- OpenAI API（AI戦略分析・決定）
- Docker（コンテナ運用）
- GitHub Actions（CI/CD、任意）

## 2. 開発ガイドライン

- 推奨 Python バージョンは **3.11** です。
- コードは PEP8 に準拠させ、`isort` で import を整列してください。
- Docstring は `pydocstyle` の基準に合わせます。
- 静的解析は `ruff`、型チェックは `mypy` を利用します。

### テスト・静的解析手順

```bash
pip install -r requirements-test.txt
ruff check .
isort .
mypy .
pytest
```

### PR 作成ルール

- ブランチ名は `feature/<内容>`、`fix/<内容>`、`docs/<内容>` の形式とします。
- PR には `## Summary` と `## Testing` セクションを含めてください。
