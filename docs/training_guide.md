# トレーニングガイド

このドキュメントでは `training/` ディレクトリにあるスクリプトの実行方法を解説します。主に以下の2つを提供しています。

- `offline_policy_learning.py`
- `train_regime_model.py`

## offline_policy_learning.py の使い方

`policy_transitions` テーブルを含む SQLite データベースからオフラインで学習し、`models/strategy_policy.pkl` に Q 学習モデルを保存します。

1. 学習に使用するデータベースを用意し、`TRADES_DB_PATH` 環境変数でパスを指定します。
2. 以下のコマンドを実行します。

```bash
export TRADES_DB_PATH=backend/logs/trades.db
python training/offline_policy_learning.py
```

学習が完了すると `models/strategy_policy.pkl` が生成されます。

## train_regime_model.py の使い方

CSV 形式のローソク足データから特徴量を抽出し、Gaussian Mixture Model を用いてレジーム分類器を学習します。モデルは `models/regime_gmm.pkl` として保存されます。

1. `high`,`low`,`close`,`volume` を含む CSV ファイルを用意します。サンプルは `training/examples/sample_rates.csv` にあります。
2. コマンドライン引数で CSV のパスを指定して実行します。

```bash
python training/train_regime_model.py training/examples/sample_rates.csv
```

指定がない場合は `tests/data/range_sample.csv` が使用されます。学習後、`models/regime_gmm.pkl` にモデルが保存されます。
