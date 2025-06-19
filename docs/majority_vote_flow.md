# 多数決パイプラインの流れ

AI モデルのノイズを抑えるため、複数ステップを組み合わせた多数決フローを用います。以下は `piphawk_ai.vote_arch` モジュールで実装されている処理の概要です。

```text
[Indicators] --> [Regime Detection]
Regime Detection --> Strategy Select (n times)
Strategy Select --vote--> Trade Mode
Trade Mode --prompt--> Entry Plan
Entry Plan --> Plan Buffer --> PipelineResult
```

## 各ステップの役割

1. **Regime Detection** – ADXとボリンジャーバンド幅から `trend` / `range` / `vol_spike` を推定します。
2. **Strategy Select** – OpenAI API を1回呼び出して `STRAT_N` 本の候補を生成し、多数決でモードを決定します。温度は `STRAT_TEMP` で調整します。
3. **Trade Mode** – 多数決が十分でない場合はレジームに応じたフォールバックを行います (`STRAT_VOTE_MIN` が閾値)。
4. **Entry Plan** – 選択されたモードをプロンプトに与え、TP/SL などの具体的なプランを生成します。
5. **Plan Buffer** – 直近 `ENTRY_BUFFER_K` 個のプランを平均化して外れ値を緩和します。

詳細な実装は `piphawk_ai/vote_arch/` ディレクトリを参照してください。

## 設定方法

環境変数 `USE_VOTE_PIPELINE` を `true` にするとこの多数決パイプラインが有効化されます。
`false` を指定した場合は [technical_pipeline.md](technical_pipeline.md) に記載の
テクニカル重視フローへ切り替わります。
こちらは戦略選択とエントリープラン生成を複数回実行し、AI のノイズを平均化する点が
テクニカルパイプラインとの大きな違いです。
