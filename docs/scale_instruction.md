# SCALE 指示の処理フロー

`exit_ai_decision.evaluate()` から `SCALE` が返った場合の基本的な流れを示します。

```text
[ポジション保有] --evaluate--> [AI判定]
          \-- EXIT --> クローズ
          \-- HOLD --> そのまま維持
          \-- SCALE -> 追加エントリー
```

サンプルコード:

```python
result = evaluate(context)
if result.action == "SCALE" and result.confidence > 0.7:
    # 例: 既存ポジションに追加のロットを乗せる
    order_manager.add_units(position, extra_units)
```

AI が SCALE を返すのは、含み益がありトレンドの継続が見込めるときです。\
実際にロットを増やす前に、証拠金規制や最大許容リスクを必ず確認してください。
