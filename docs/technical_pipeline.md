# M5 即エントリー × AI TP チューナー フロー

PipHawk が採用する最新の最小フィルタ構成です。M5 シグナルを直接トリガーとし、AI で TP/SL 倍率を調整します。

環境変数 `USE_VOTE_PIPELINE` を `false` にすると、ジョブランナーはこのテクニカルパイプラインを実行します。`true` の場合は [majority_vote_flow.md](majority_vote_flow.md) で説明する多数決パイプラインが利用されます。

以下の順序で処理が進みます。

0. **テクニカル指標計算** – AI を使わずに主要指標を算出します。
1. **フィルター** – 市場が開いているか、禁止時間外か、底ボラ・スプレッド拡大をチェックします。
2. **戦略選択** – レジームを判定し、スキャルプかトレンドかを決定します。
3. **AI 判断** – ローソク足パターンと計算済み指標を基にロング・ショートを判定します。
4. **TP/SL 設定** – ボラティリティを考慮して適切な TP と SL を配置します。
5. **エントリー** – すべての条件を満たしたら必ず注文を発行します。

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

    %% ===== 3. M5 SIGNAL =====
    SIG[5. M5 シグナル検出<br>• 高値/安値ブレイク<br>• BB±2σ 反発包み足]
    MCL --> SIG
    SIG -- None --> SCHED

    %% ===== 4. ENTRY TP TUNER =====
    AI_ON{ENTRY_USE_AI?}
    subgraph AI[6a. AI TP Tuner]
        direction TB
        PAYLOAD[[JSON Payload<br>(pair, mode, signal,<br>M5 + H1/H4 指標, cost,<br>default TP/SL)]]
        LLM[[OpenAI<br>chat.completions]]
        RESP[[{tp_mult,<br>sl_mult, rationale}]]
    end
    SIG -- signalOK --> AI_ON
    AI_ON -- "false" --> TPSL
    AI_ON -- "true" --> PAYLOAD --> LLM --> RESP

    %% ===== 5. ORDER =====
    TPSL[7. TP/SL 計算<br>ATR×{tp,sl}_mult]
    RESP --> TPSL
    ORD[OrderManager.place_order()]
    TPSL --> ORD

    %% ===== 6. LOG & NOTIFY =====
    LOG[8. trade_signals DB / Prometheus / LINE]
    ORD --> LOG --> SCHED
```

---

## ステップ要約

| # | ブロック | 中身 | 出口条件 |
|---|---|---|---|
|1|MarketContext / IndicatorEngine|M5×3・Tick・Spread＋主要指標計算|Price/Indicators 準備完了|
|2|market_classifier.classify_market|ADX14・EMA50乖離・BB 幅 …|mode = "trend" or "range"|
|3|m5_entry.detect_entry|Trend:高値/安値ブレイク Range:包み足反発|None→skip|
|4|ai_decision.call_llm (optional)|ENTRY_USE_AI=true なら LLM へ TP 倍率だけ取得|なし|
|5|tpsl_calc → order_manager|ATR×倍率で TP/SL, 発注 (ENTRY_USE_AI=false 時は既定倍率)|注文 ID 取得|
|6|Logger / Metrics / LINE|DB 保存・Prometheus カウント・通知|ループ完了|

EXIT ロジック（トレイリング SL, 時間切れ, AI exit 等）は既存のままで TP/SL に追随します。

これが最新の最小フィルタ × M5 即エントリー × AI TP チューナー フローです。


多数決パイプラインと異なり、指標ベースでシンプルに判定を行う点が特徴です。AI は
TP/SL 調整のみで使用され、戦略選択や投票処理は行いません。
### ENTRY_USE_AI

環境変数 `ENTRY_USE_AI` を `false` にすると、LLM への問い合わせを行わずに既定の TP/SL 倍率を用いてエントリーします。`backend/scheduler/job_runner.py` もこの変数を参照し、無効時は本パイプラインを用いて発注を行います。

