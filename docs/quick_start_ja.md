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
   docker build -t piphawk-ai .
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
