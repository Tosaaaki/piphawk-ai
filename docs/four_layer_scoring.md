# 4 レイヤー・スコアリングと TP/SL 最適化

本システムではエントリーの可否を多角的に判断するため、4 つのレイヤーからなるスコアリング手法を導入しました。各レイヤーは次の要素を評価し、0〜1 の値で貢献度を返します。

1. **トレンドレイヤー** – EMA 方向や高位足の位置関係を基にした長期トレンド判定
2. **モメンタムレイヤー** – ADX 変化量やボリューム増加率から現在の勢いを測定
3. **ボラティリティレイヤー** – ATR 幅や Bollinger Band 拡張度合いを参照
4. **パターンレイヤー** – ローソク足パターンや AI 解析結果

最終スコアは各レイヤー値に重みを掛け、合計を重みの総和で割ることで算出します。

```python
score = (trend*w1 + momentum*w2 + volatility*w3 + pattern*w4) / (w1+w2+w3+w4)
```

重みは環境変数 `SCORE_WEIGHTS` で設定できます。`ENTRY_SCORE_MIN` を超えた場合にのみエントリーが許可されます。

## TP/SL 最適化アルゴリズム

取引ごとの期待値を高めるため、複数候補の TP/SL 組み合わせを評価し、最も EV (Expected Value) が高いものを採用します。各候補は成功確率 `p` と TP/SL 幅 `tp`、`sl` を持ち、期待値は以下の式で計算されます。

```python
EV = tp * p - sl * (1 - p)
```

`MIN_RRR` と `ENFORCE_RRR` を併用すると、リスクリワード比を維持しつつ最適な組み合わせを選択できます。

### 設定例

```env
SCORE_WEIGHTS=trend:0.4,momentum:0.3,volatility:0.2,pattern:0.1
ENTRY_SCORE_MIN=0.6
TP_CANDIDATES=10,15,20
SL_CANDIDATES=8,10,12
MIN_RRR=1.3
ENFORCE_RRR=true
```
