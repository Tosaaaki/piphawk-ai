# 適応型ポリシーとレジーム認識のアーキテクチャ

本ドキュメントでは、レジーム認識層・戦略ポートフォリオ層・リスクエンジンを統合した
システム設計の概要を示します。実装例や既存コードへの関連付けもあわせてまとめます。

## 1. レジーム認識層

- 価格・テクニカル指標・オーダーフローから特徴量を生成し、GMM あるいは HDBSCAN に
  よるクラスタリングで市場レジームを分類します。
- 主要な特徴量として ATR・ADX などのテクニカル値を `indicators/rolling.py` で計算しま
  す【F:backend/indicators/rolling.py†L24-L48】。
- 学習済みモデルは `models/` 以下に保存し、ジョブランナー起動時に読み込みます。

## 2. 戦略ポートフォリオ層

- 複数戦略から成るアームを Contextual Multi-Armed Bandit で選択します。
- 例として `mabwiser` ライブラリの LinUCB を利用し、レジームラベルと直近パフォーマ
  ンスをコンテキストにします。
- 戦略実装は `strategies/` 配下に配置し、`selector.py` でバンディットロジックを管理し
  ます。

## 3. 統合リスクエンジン

- ロット数計算や TP/SL 管理は `strategy/risk_manager.py` の `calc_lot_size` に代表される
  関数群で処理します【F:backend/strategy/risk_manager.py†L1-L12】。
- ポジション全体のリスクを CVaR 等で監視し、必要に応じてポジション縮小や強制決済を
  行います。
- ストップロス・トレーリングは `strategy/exit_logic.py` にまとめられています
  【F:backend/strategy/exit_logic.py†L15-L24】。

## 4. ポリシー学習

- 過去ログから Offline RL (例: d3rlpy の BCQ/CQL) を実施し、戦略選択ポリシーを改善し
  ます。
- オンラインでは Thompson Sampling 等で逐次更新を行い、環境変化に追従します。

## 5. 可観測性

- Kafka → Prometheus → Grafana による監視基盤を想定し、戦略選択やリスクイベントを
  リアルタイムで可視化します。

## 6. AI モデルの役割

- LLM を用いたニュース解析モジュール `ai/macro_analyzer.py` を設け、定性的情報を
  レジーム認識に取り込みます。応答遅延を避けるため非同期処理や軽量モデル切り替えを
  可能にします。

## 7. ディレクトリ構成例

```
project-root/
├── regime/          # レジーム検知ユーティリティ
├── strategies/      # 個別戦略とバンディット選択
├── risk/            # リスク管理エンジン
├── ai/              # ニュース解析やプロンプト雛形
├── monitoring/      # Kafka プロデューサと Prometheus エクスポータ
└── models/          # 学習済みモデル保存先
```

これらのコンポーネントを連携させることで、市場環境の変化に応じた自律的な
ポリシー更新とリスク制御が実現できます。
