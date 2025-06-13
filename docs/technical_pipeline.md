# M5 即エントリー × AI TP チューナー フロー

PipHawk が採用する最新の最小フィルタ構成です。M5 シグナルを直接トリガーとし、AI で TP/SL 倍率を調整します。

環境変数 `USE_VOTE_PIPELINE` を `false` にすると、ジョブランナーはこのテクニカルパイプラインを実行します。`true` の場合は [majority_vote_flow.md](majority_vote_flow.md) で説明する多数決パイプラインが利用されます。

```mermaid
flowchart TD
    %% ===== 0. LOOP =====
    SCHED[[Scheduler<br>(≈ 4 s周期)]]

    %% ===== 1. SNAPSHOT =====
    subgraph SNAP[1. 市場スナップショット]
        direction TB
        CXT[MarketContext.build()<br>• 最新 M5 × 3 本<br>• Tick 現値・Spread]
        IND[IndicatorEngine<br>• ADX14 / EMA50<br>• ATR / BB / RSI<br>• H1/H4 ADX & EMA]
    end
    SCHED --> CXT --> IND

    %% ===== 2. MARKET CLASSIFY =====
    MCL[2. Range / Trend 分類<br>(ADX & EMA 乖離)]
    IND --> MCL

    %% ===== 3. RISK FILTERS =====
    subgraph RISK[3. 簡易リスクフィルタ]
        direction TB
        F1[spread ≤ ATR×0.15]
        F2[marginAvailable > 5 %]
        F3[duplicateGuard]
        F4[volSpikeGuard]
    end
    MCL --> RISK
    RISK -- NG --> SCHED

    %% ===== 4. M5 SIGNAL =====
    SIG[4. M5 シグナル検出<br>• 高値/安値ブレイク<br>• BB±2σ 反発包み足]
    RISK -- OK --> SIG
    SIG -- None --> SCHED

    %% ===== 5. AI GATE & TP TUNE =====
    subgraph AI[5. AI Decision & TP Tuner]
        direction TB
        PAYLOAD[[JSON Payload<br>(pair, mode, signal,<br>M5 + H1/H4 指標, cost,<br>default TP/SL)]]
        LLM[[OpenAI<br>chat.completions]]
        RESP[[{decision, tp_mult,<br>sl_mult, rationale}]]
    end
    SIG -- signalOK --> PAYLOAD --> LLM --> RESP
    RESP -- decision:PASS --> SCHED

    %% ===== 6. ORDER =====
    TPSL[6. TP/SL 計算<br>ATR×{tp,sl}_mult]
    RESP -- decision:GO --> TPSL
    ORD[OrderManager.place_order()]
    TPSL --> ORD

    %% ===== 7. LOG & NOTIFY =====
    LOG[7. trade_signals DB / Prometheus / LINE]
    ORD --> LOG --> SCHED
```

---

## ステップ要約

| # | ブロック | 中身 | 出口条件 |
|---|---|---|---|
|1|MarketContext / IndicatorEngine|M5×3・Tick・Spread＋主要指標計算|Price/Indicators 準備完了|
|2|market_classifier.classify_market|ADX14・EMA50乖離・BB 幅 …|mode = "trend" or "range"|
|3|簡易リスクフィルタ|スプレッド／証拠金／重複／異常ボラ|NG→skip|
|4|m5_entry.detect_entry|Trend:高値/安値ブレイク Range:包み足反発|None→skip|
|5|ai_decision.call_llm|JSON で LLM へ Go/PASS と TP チューニング依頼|PASS→skip|
|6|tpsl_calc → order_manager|ATR×倍率で TP/SL, 発注|注文 ID 取得|
|7|Logger / Metrics / LINE|DB 保存・Prometheus カウント・通知|ループ完了|

EXIT ロジック（トレイリング SL, 時間切れ, AI exit 等）は既存のままで TP/SL に追随します。

これが最新の最小フィルタ × M5 即エントリー × AI TP チューナー フローです。

多数決パイプラインと異なり、指標ベースでシンプルに判定を行う点が特徴です。AI は
TP/SL 調整のみで使用され、戦略選択や投票処理は行いません。
