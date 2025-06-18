# 積極的なスキャルプ設定

スキャルプモードでより頻繁にエントリーしたい場合は、以下の環境変数を調整します。

## 推奨値

- `ENABLE_RANGE_ENTRY=true`  
  ADX が低くてもレンジ内でエントリーを許可します。
- `BAND_WIDTH_THRESH_PIPS=0`  
  ボリンジャーバンド幅によるレンジ判定を無効化します。
- `SCALP_ADX_MIN=15`
  必要なADXしきい値をより下げます。
- `BYPASS_PULLBACK_ADX_MIN=20`
  これを超えるとプルバック待機を省略します。
- `AI_COOLDOWN_SEC_FLAT=15`  
  ノーポジ時のAIクールダウンを短縮します。
- `MIN_RRR=1.0`
- `ENFORCE_RRR=false`
- `SCALP_TP_PIPS=8`
- `SCALP_SL_PIPS=8`
- `SCALP_PROMPT_BIAS=aggressive`
- `AI_RETRY_ON_NO=false`  # このオプションは廃止されました

## マイクロ構造モードの有効化

Tick データから超短期エントリーを判定する `openai_micro_scalp.py` を使う場合は、
以下を `.env` に追加します。

```bash
MICRO_SCALP_ENABLED=true
MICRO_SCALP_LOOKBACK=5
MICRO_SCALP_MIN_PIPS=1
```

設定後にジョブランナーを再起動するとマイクロ構造モードが有効になります。

## Quick TP モード

AI で方向を判断し 2pips で利確する超短期売買を繰り返す場合は以下を設定します。

```bash
QUICK_TP_MODE=true
QUICK_TP_INTERVAL_SEC=360
QUICK_TP_UNITS=1000
```

有効化すると通常のジョブランナー処理は実行されず、このモードのみが動作します。

## 反映手順

1. `backend/config/settings.env` に上記を追記または変更します。
2. `docker compose restart piphawk-runner` でコンテナを再起動します。
3. 起動ログで新しい値が読み込まれていることを確認します。
