# 主要環境変数リファレンス

アプリケーションが参照する環境変数の優先順位は
**外部で設定された値 → `.env` → `backend/config/settings.env` → `backend/config/secret.env`**
の順になります。よく使う変数を以下にまとめます。

| 変数 | デフォルト値 | 用途 | 設定例 |
|---|---|---|---|
| OPENAI_API_KEY | (なし) | OpenAI API キー | `OPENAI_API_KEY=sk-...` |
| OANDA_API_KEY | (なし) | OANDA API キー | `OANDA_API_KEY=your-token` |
| OANDA_ACCOUNT_ID | (なし) | OANDA 取引口座ID | `OANDA_ACCOUNT_ID=001-1234567-001` |
| DEFAULT_PAIR | USD_JPY | 取引する通貨ペア | `DEFAULT_PAIR=EUR_USD` |
| TRADES_DB_PATH | /app/backend/logs/trades.db | 取引履歴DBの保存先 | `TRADES_DB_PATH=trades.db` |
| AI_MODEL | gpt-3.5-turbo-0125 | 汎用OpenAIモデル | `AI_MODEL=gpt-3.5-turbo-0125` |
| AI_ENTRY_MODEL | gpt-3.5-turbo-0125 | エントリー判断モデル | `AI_ENTRY_MODEL=gpt-3.5-turbo-0125` |
| AI_EXIT_MODEL | gpt-3.5-turbo-0125 | エグジット判断モデル | `AI_EXIT_MODEL=gpt-3.5-turbo-0125` |
| MIN_RRR | 0.9 | 最低リスクリワード比 | `MIN_RRR=1.2` |
| ENFORCE_RRR | false | RRRを強制するか | `ENFORCE_RRR=true` |
| AI_COOLDOWN_SEC_OPEN | 60 | ポジション保有時のAI待機秒 | `AI_COOLDOWN_SEC_OPEN=30` |
| AI_COOLDOWN_SEC_FLAT | 15 | ノーポジ時のAI待機秒 | `AI_COOLDOWN_SEC_FLAT=30` |
| MIN_TRADE_LOT | 30.0 | 最小ロット数 | `MIN_TRADE_LOT=10` |
| MAX_TRADE_LOT | 40.0 | 最大ロット数 | `MAX_TRADE_LOT=100` |
| SCALE_LOT_SIZE | 0.5 | 追加エントリー時のロット | `SCALE_LOT_SIZE=0.3` |
| MIN_SL_PIPS | 8 | 最小ストップ幅(pips) | `MIN_SL_PIPS=10` |
| TRAIL_ENABLED | true | トレーリングストップ有効化 | `TRAIL_ENABLED=false` |
| TRAIL_TRIGGER_PIPS | 22 | トレーリング発動幅(pips) | `TRAIL_TRIGGER_PIPS=30` |
| TRAIL_DISTANCE_PIPS | 6 | トレーリング距離(pips) | `TRAIL_DISTANCE_PIPS=8` |
| LINE_CHANNEL_TOKEN | (なし) | LINE通知トークン | `LINE_CHANNEL_TOKEN=xxxx` |
| LINE_USER_ID | (なし) | LINE通知先ユーザーID | `LINE_USER_ID=yyyy` |
| CORS_ALLOW_ORIGINS | (なし) | APIで許可するオリジン | `CORS_ALLOW_ORIGINS=http://localhost:3000` |
| LOG_LEVEL | INFO | ログ出力レベル | `LOG_LEVEL=DEBUG` |
| ATMOS_EMA_WEIGHT | 0.4 | AtmosphereモジュールでEMA傾きを評価する重み | `ATMOS_EMA_WEIGHT=0.5` |
| ATMOS_RSI_WEIGHT | 0.3 | AtmosphereモジュールのRSI重み | `ATMOS_RSI_WEIGHT=0.2` |
| ATMOS_THRESHOLD | 0.5 | Atmosphereスコアがこの値以上ならエントリー | `ATMOS_THRESHOLD=0.6` |

より詳細な変数や追加の設定は [docs/env_vars.md](env_vars.md) を参照してください。
