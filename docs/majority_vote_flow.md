# 多数決パイプラインの流れ

AI モデルのノイズを抑えるため、複数ステップを組み合わせた多数決フローを用います。以下は `piphawk_ai.vote_arch` モジュールで実装されている処理の概要です。

```text
[Indicators] --pass_entry_filter--> [Regime Detection]
                 \-- NG --> stop
Regime Detection --prompt--> Strategy Select (n times)
Strategy Select --vote--> Trade Mode
Trade Mode --prompt--> Entry Plan
Entry Plan --> Plan Buffer --> Final Filter --> PipelineResult
```

## 各ステップの役割

1. **pass_entry_filter** – RSI やATRなどの指標から事前条件を判定し、不適切な状況では早期に終了します。
2. **Regime Detection** – ADXとボリンジャーバンド幅から `trend` / `range` / `vol_spike` を推定します。
3. **Strategy Select** – OpenAI API を複数回呼び出し、`STRAT_N` 本の候補から多数決でモードを決定します。温度は `STRAT_TEMP` で調整します。
4. **Trade Mode** – 多数決が十分でない場合はレジームに応じたフォールバックを行います (`STRAT_VOTE_MIN` が閾値)。
5. **Entry Plan** – 選択されたモードをプロンプトに与え、TP/SL などの具体的なプランを生成します。
6. **Plan Buffer** – 直近 `ENTRY_BUFFER_K` 個のプランを平均化して外れ値を緩和します。
7. **Final Filter** – EMA 乖離やリスクリワード比を再確認し、条件を満たした場合のみ採用します。

詳細な実装は `piphawk_ai/vote_arch/` ディレクトリを参照してください。
