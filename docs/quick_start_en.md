# QuickStart

1. Clone the repository

   ```bash
   git clone https://github.com/yourname/piphawk-ai.git
   cd piphawk-ai
   ```

2. Create .env from example

   ```bash
   cp backend/config/secret.env.example .env
   ```

   Edit `.env` and set OPENAI_API_KEY, OANDA_API_KEY and OANDA_ACCOUNT_ID.
3. Build and run the backend container

   ```bash
   DOCKER_BUILDKIT=1 docker build -t piphawk-ai .
   docker run --env-file .env -p 8080:8080 \
     -v $(pwd)/backend/logs:/app/backend/logs piphawk-ai
   ```

4. Start the React UI

   ```bash
   cd piphawk-ui
   npm install
   npm start
   ```

Past performance does not guarantee future results. Use at your own risk.

When the AI returns `side: "no"`, the plan includes a `why` field briefly stating the reason. When it responds with `side: "yes"`, the `risk` object must contain `tp_pips`, `sl_pips`, `tp_prob` and `sl_prob`; `tp_prob` should be at least 0.70.
