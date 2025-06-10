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
- `SCALP_TP_PIPS=4`
- `SCALP_SL_PIPS=4`
- `SCALP_PROMPT_BIAS=aggressive`
- `AI_RETRY_ON_NO=true`

## 反映手順

1. `backend/config/settings.env` に上記を追記または変更します。
2. `docker compose restart piphawk-runner` でコンテナを再起動します。
3. 起動ログで新しい値が読み込まれていることを確認します。
