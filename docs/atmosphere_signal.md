# Atmosphere Signal

Atmosphere モジュールは VWAP 乖離率と Volume Delta を用いて市場の"雰囲気"を数値化します。`AtmosphereFeatures` で特徴量を計算し、`AtmosphereScore` で 0--100 点のスコアへ変換します。`RegimeClassifier` を使うと Risk-On/Off のタグに分類できます。

```python
from analysis.atmosphere.feature_extractor import AtmosphereFeatures
from analysis.atmosphere.score_calculator import AtmosphereScore
from analysis.atmosphere.regime_classifier import RegimeClassifier
from signals.atmosphere_signal import generate_signal

candles = [
    {"open": 100, "close": 101, "volume": 10},
    {"open": 101, "close": 102, "volume": 12},
]

features = AtmosphereFeatures(candles).extract()
score = AtmosphereScore().calc(features)
regime = RegimeClassifier().classify(score)
entry = generate_signal(score, rsi=25)
```

`generate_signal` は RSI とスコアを組み合わせ、条件を満たすと ``"long"`` または ``"short"`` を返します。
