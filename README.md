# Piphawk AI

Piphawk AI is an automated trading system that uses the OANDA REST API for order management and integrates OpenAI models for market analysis. The project provides a REST API for monitoring and runtime configuration as well as a job runner that executes the trading logic at a fixed interval.

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourname/piphawk-ai.git
   cd piphawk-ai
   ```
2. **Install dependencies**
   It is recommended to use a virtual environment.
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```
3. **Environment variables**
   Copy the sample configuration files and edit them with your credentials:
   ```bash
   cp backend/config/secret.env .env
   cp backend/config/settings.env .
   ```
   Edit `.env` and set `OPENAI_API_KEY`, `OANDA_API_KEY` and `OANDA_ACCOUNT_ID`.
   The application automatically loads `.env`, `backend/config/settings.env` and
   `backend/config/secret.env` once at startup using `backend.utils.env_loader`.
   Adjust any values in `settings.env` as needed.

## Running the API

The API exposes endpoints for status checks, a simple dashboard and runtime settings. Start it with Uvicorn:
```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port 8080
```

## Running the Job Scheduler

The job runner performs market data collection, indicator calculation and trading decisions. Run it directly with Python:
```bash
python -m backend.scheduler.job_runner
```

Both services can also be launched via Docker using `Dockerfile.api` and `Dockerfile.job` respectively.

## Database

Trade history is stored in `trades.db` (SQLite). A pre-populated file is provided in `backend/logs/` for testing. When running inside Docker the database is copied to `/app/trades.db`.

## React UI

The `piphawk-ui/` directory contains a full React application built with Create React App. Run it locally with:

```bash
cd piphawk-ui
npm install
npm start
```

Node.js **14 or later** is required (Node 18 LTS recommended). The React UI is
built with **React 18** and should be run with that major version.

## License

This project is provided as-is under the MIT license.

## Frontend Components

The `frontend/` directory contains example React components styled with `styled-components` for a dark dashboard UI:

- `Dashboard.jsx` – trade history table, performance summary, and a line chart placeholder.
- `Settings.jsx` – controls for numeric and boolean parameters with sliders and toggles.
- `ContainerControls.jsx` – start/stop/restart buttons with spinner indicators.
- `LogViewer.jsx` – tabbed viewer showing errors and recent trades.

These components are examples only and are not yet integrated into a build setup.


