# テクニカル判定版エントリー・パイプライン

以下のフローではテクニカル指標のみでエントリー可否を決定します。

```mermaid
flowchart TD
    A0[0. Scheduler<br>ループ=~4 s] --> A1
    subgraph Market Snapshot
        A1[1. MarketContext.build()<br>• M5 Candle / Ticks<br>• 口座・スプレッド]
        A2[2. IndicatorEngine<br>EMA, ATR, ADX, BB, RSI…]
    end
    A2 --> A3

    subgraph Mode Detect (100 % Tech)
        A3[3. ModeDetector.detect_mode()<br>
            ─ Trend         ⇒ ADX>25 & EMA50>EMA200 & ATR比率
            ─ ScalpMomentum ⇒ BB±2σ ブレイク & EMA9>EMA21 & TickATR↑
            ─ ScalpReversal ⇒ RSI7 極値 & BB±3σ 反転 & ADX7<20
            ─ Range         ⇒ 上記以外]
    end
    A3 --> B0

    subgraph Prefilter
        B0[4. Generic Prefilters<br>spread / margin / time]
    end
    B0 -- NG --> A0
    B0 -- OK --> B1

    subgraph Mode-Specific Filters
        B1{{モード分岐}}
        B2[4-T. Trend Filters<br>EMA乖離, ATR拡大 …]
        B3[4-S. Scalp Filters<br>無し (Trend専用のみskip)]
        B1 -->|Trend系| B2
        B1 -->|Scalp系| B3
        B2 -- NG --> A0
        B2 -- OK --> C0
        B3 --> C0
    end

    subgraph Decision
        C0[5. LLM Entry Gate<br>OpenAI に「入る/パス」を尋ねる] --> C1
        C1[6. RuleValidator<br>RRR, 2/3 ルール]
        C1 -- fail --> A0
    end
    C1 -- pass --> D0

    subgraph Safety & Order
        D0[7. PostFilters<br>Overshoot, Duplicate…] --> D1
        D1[8. OrderManager.place_order()<br>OANDA REST] --> D2
    end
    D1 -- NG --> A0
    D2 --> E0

    subgraph Persist & Notify
        E0[9. DB / Prometheus / LINE]
    end
    E0 --> A0
```

この手順は `piphawk_ai.tech_arch` モジュールで実装されています。
