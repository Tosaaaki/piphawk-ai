# ブレイクアウト追随エントリー

`follow_breakout` 関数はレンジブレイク後の押し戻しを利用してエントリーすべきかどうかを判定します。

```python
from backend.strategy.momentum_follow import follow_breakout

# candles は直近のローソク足リスト、indicators は計算済み指標
if follow_breakout(candles, indicators, "up"):
    # エントリー処理を実行
    pass
```

実装内部では押し戻し量や ADX を用いて判断する想定ですが、現時点では TODO として残しています。
