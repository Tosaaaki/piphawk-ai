# ブレイクアウト追随エントリー

`follow_breakout` 関数はレンジブレイク後の押し戻しを利用してエントリーすべきかどうかを判定します。

```python
from backend.strategy.momentum_follow import follow_breakout

# candles は直近のローソク足リスト、indicators は計算済み指標
if follow_breakout(candles, indicators, "up"):
    # エントリー処理を実行
    pass
```

実装では直近の押し戻し量が ATR の一定割合以内かつ ADX が閾値以上かを確認してエントリー可否を判定します。
