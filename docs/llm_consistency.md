# LLMトレード判定の一貫性向上メモ

本ドキュメントでは、AIによるエントリー・エグジット判定が不安定になる原因と、改善のためのプロンプト設計方針をまとめます。

## 1. 不整合が起きる主な原因

- **プロンプト設計**: 役割や評価基準が曖昧だと、モデルが判断軸を変えやすい。
- **コンテキスト量**: 重要なローソク足や履歴が欠けると連続性が失われる。
- **帰納型質問**: 数値を答えさせてから結論を促すと内部計算誤差が影響する。
- **決定ルール未固定**: 閾値や優先度を毎回推測させると揺らぎが大きい。
- **頻繁な呼び出し**: 温度が高い状態で連続質問すると出力がブレやすい。
- **外部要因**: モデルのバージョン違いやフォールバックが混在すると形式が崩れる。

## 2. 改善方針

1. **役割固定**: "あなたはUSD/JPY専用のリスクマネージャ" など明示する。
2. **入力項目を固定**: JSON形式で市場データを渡し、余計な文章を省く。
3. **閾値をコードで渡す**: `params.exit_loss_pips=-5` のように埋め込み、推測させない。
4. **温度0と少数決**: 決定論的な出力を基本とし、必要に応じてバックアップ評価を行う。
5. **JSON出力固定**: `decision`, `reason`, `confidence` のみ返すよう義務付ける。

## 3. サンプルプロンプト

テンプレートとして `prompts/entry_coach.yaml` と `prompts/exit_manager.yaml` を用意しました。変数を差し替えて使用します。

```yaml
# entry_coach.yaml (抜粋)
system: |
  You are the dedicated USD/JPY scalping entry coach.
  ...
user: |
  market = {{market}}
  params = {{params}}
```

```yaml
# exit_manager.yaml (抜粋)
system: |
  You are the risk manager for USD/JPY positions.
  ...
user: |
  position = {{position}}
  market = {{market}}
  rules = {{rules}}
```

## 4. 実装メモ

- テンプレートは YAML/JSON で保存し、サーバ側で変数置換してから送信します。
- `decision` が `UNKNOWN` の場合は無視するフェイルセーフを入れてください。
- API 本番運用前にドライランを行い、AIの判断と実際の値動きを突き合わせて検証します。
