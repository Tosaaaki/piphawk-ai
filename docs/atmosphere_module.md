# Atmosphere Module

市場の"雰囲気"を数値化し、戦略重みを調整する拡張モジュールです。EMAの傾きやRSIバイアスからスコアを算出し、一定値を超えたときのみエントリーを許可します。

## Usage

```python
from backend.analysis.atmosphere import evaluate

score, bias = evaluate(context)
```

`bias` はリスク割合などの自動調整に利用できます。

## Environment Variables

- `ATMOS_EMA_WEIGHT` — EMA傾きをスコアへ加える重み (default: 0.4)
- `ATMOS_RSI_WEIGHT` — RSIバイアスの重み (default: 0.3)
- `ATMOS_THRESHOLD` — エントリーを許可する最小スコア (default: 0.5)

`.env` へこれらの値を設定して挙動をカスタマイズしてください。
