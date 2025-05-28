# ブレイクアウト追随エントリー

`follow_breakout` 関数はレンジブレイク後の押し戻しを利用してエントリーすべきかどうかを判定します。

```python
from backend.strategy.momentum_follow import follow_breakout

# candles は直近のローソク足リスト、indicators は計算済み指標
if follow_breakout(candles, indicators, "up"):
    # エントリー処理を実行
    pass
```

関数は以下の手順で判定を行います。

1. 指標辞書から `adx` と `atr` の最新値を取得します。
2. `FOLLOW_ADX_MIN` 以上の ADX が確認できなければ `False` を返します。
3. ブレイクアウト足（直前の足）と現在の足との終値差を計算し、押し戻し幅を求めます。
4. 押し戻し幅を ATR と比較し、`FOLLOW_PULLBACK_ATR_RATIO` × ATR 以下なら `True` を返します。

戻り値は `True` または `False` で、ポジションを追随させるかどうかの判断に使えます。
