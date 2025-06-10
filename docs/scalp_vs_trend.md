# スキャルプ用とトレンドフォロー用の設定分離

このドキュメントではスキャルプ戦略とトレンドフォロー戦略のパラメータを
別々のファイルにまとめて管理する方法を紹介します。`config/strategy.yml`
を複数用意し、`params_loader.load_params()` に読み込ませるだけで簡単に
切り替えられます。

## プロファイルファイルの作成

例として `config/scalp_params.yml` と `config/trend.yml` を作成し、
それぞれスキャルプ向け、トレンド向けの値を記述します。

`config/scalp_params.yml` の例:

```yaml
SCALP_MODE: true
ENABLE_RANGE_ENTRY: true
BAND_WIDTH_THRESH_PIPS: 0
SCALP_ADX_MIN: 20
BYPASS_PULLBACK_ADX_MIN: 25
AI_COOLDOWN_SEC_FLAT: 15
MIN_HOLD_SECONDS: 300
```

`config/trend.yml` の例:

```yaml
SCALP_MODE: false
ADX_TREND_MIN: 35
TREND_COND_TF: M5
TRAIL_TRIGGER_PIPS: 20
TRAIL_DISTANCE_PIPS: 10
PARTIAL_CLOSE_PIPS: 10
PARTIAL_CLOSE_RATIO: 0.5
```

## 共通パラメータ

`ENABLE_RANGE_ENTRY` や `BAND_WIDTH_THRESH_PIPS`、`BYPASS_PULLBACK_ADX_MIN`
などはスキャルプ・トレンド両方で利用されます。必要に応じて各 YAML に
同じ値を記載してください。

## 使い方

プログラムから特定のプロファイルを読み込む場合は
`params_loader.load_params()` にファイルパスを渡します。

```python
from config import params_loader
params_loader.load_params(path="config/scalp_params.yml")
```

`backend/scheduler/job_runner.py` ではデフォルトで
`config/strategy.yml` を読み込むため、実行前に目的の YAML
を `strategy.yml` へコピーしておくのも簡単です。

## 運用上の注意

環境変数は従来通り `backend/config/settings.env` を基準に読み込まれます。
YAML はあくまで設定を切り替えるためのオプションで、`params_loader.load_params()`
を呼び出したタイミングで反映されます。デフォルトの `job_runner.py` は
起動時に一度だけ `strategy.yml` を読み込むため、YAML を編集しただけでは
ランタイム中に値は変わりません。変更を反映するにはジョブランナーを再起動
するか、必要に応じて `params_loader.load_params()` を再度実行してください。

## 自動切り替え

`signals.composite_mode.decide_trade_mode()` が返すモードに応じて
`backend/scheduler/job_runner.py` は `config/scalp_params.yml` もしくは
`config/trend.yml` を自動で読み込みます。モードが変化した際は
`params_loader.load_params()` を実行し、`AUTO_RESTART=true` を設定すると
読み込み後にプロセスを再起動します。
