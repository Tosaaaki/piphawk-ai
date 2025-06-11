# クイックスタート

1. リポジトリをクローン

   ```bash
   git clone https://github.com/yourname/piphawk-ai.git
   cd piphawk-ai
   ```

2. `.env` を作成

   ```bash
   cp backend/config/secret.env.example .env
   ```

   `.env` に OANDA と OpenAI の API キーを設定します。
3. Docker イメージをビルド

   ```bash
   DOCKER_BUILDKIT=1 docker build -t piphawk-ai .
   docker run --env-file .env -p 8080:8080 \
     -v $(pwd)/backend/logs:/app/backend/logs piphawk-ai
   ```

4. React UI を起動

   ```bash
   cd piphawk-ui
   npm install
   npm start
   ```

過去の実績は将来の成果を保証するものではありません。利用は自己責任で行ってください。

## よくあるエントリースキップ理由

AI から "side: \"no\"" が返り、ログに以下のような行が出る場合は TP がスプレッド控除後の下限を満たしていないことが原因です。

```text
INFO:root:Net TP 0.3 < 1.0 → skip entry
```

プランには `"reason": "NET_TP_TOO_SMALL"` と記録されます。`MIN_NET_TP_PIPS` を 0.5 程度まで下げる、あるいはスプレッドが狭い時間帯を選ぶとエントリーされやすくなります。

AI が `side: "no"` を返した場合は `why` フィールドに理由が英語で簡潔に記載されます。`side: "yes"` のときは `risk.tp_pips`, `risk.sl_pips` などが必須で、`tp_prob` は 0.70 以上である必要があります。
