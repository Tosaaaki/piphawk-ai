# Exitログの使い方

`exit_logic.py` はトレーリングストップを設定するたびに `backend/logs/exit_log.jsonl` に JSON を追記します。各行は単一の JSON オブジェクトです。

```json
{"timestamp": "2024-01-01T00:00:00Z", "instrument": "USD_JPY", "price": 155.12, "spread": 0.2, "atr": 1.5}
```

保存されたログから TP までの乖離を集計するには `backend/logs/daily_summary.py` を実行します。直近 1 日分のデータを読み取り、`tp_distance_hist.png` を生成します。

```bash
python -m backend.logs.daily_summary
```
