# =========================
# settings.env 説明ファイル
# =========================

■ DEFAULT_PAIR
取引対象とする通貨ペア（例: USD_JPY）

■ INITIAL_TP_PIPS / INITIAL_SL_PIPS
初期の利確（TP）・損切り（SL）幅（単位: pips）
※AIがこれを上書きする可能性あり

■ AI_MODEL
利用するOpenAIモデル名（gpt-4-turbo / gpt-4oなど）

■ RSI_PERIOD
RSI指標の計算期間。一般的には14が標準。

■ EMA_PERIOD
EMA（指数平滑移動平均）の計算期間。

■ ATR_PERIOD
ATR（ボラティリティ指標）の計算期間。

■ BOLLINGER_WINDOW / BOLLINGER_STD
ボリンジャーバンドの移動平均期間と標準偏差設定。

■ TRADE_LOT_SIZE
1トレードで使用するロットサイズ（1 = 1000通貨）

■ フィルター設定（AI呼び出し制御用）

- RSI_ENTRY_LOWER / RSI_ENTRY_UPPER:
  RSIがこの範囲にある時だけエントリーフィルターを通過

- ATR_ENTRY_THRESHOLD:
  ATR（ボラティリティ）がこの値より大きいときだけAI判断を許可

- EMA_DIFF_THRESHOLD:
  価格とEMAの乖離率がこの値を超えるとトレンド発生と判断

- BB_POSITION_THRESHOLD:
  ボリンジャーバンドの上限・下限に対する価格の相対位置（0〜1）をしきい値とする