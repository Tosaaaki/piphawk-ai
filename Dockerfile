FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY analysis /app/analysis
COPY ai /app/ai
COPY signals /app/signals
COPY indicators /app/indicators
COPY monitoring /app/monitoring
COPY risk /app/risk
COPY strategies /app/strategies
COPY regime /app/regime
COPY config /app/config
COPY pyproject.toml /app/pyproject.toml
COPY piphawk_ai /app/piphawk_ai

# install project as package
RUN pip install --no-cache-dir .

# create an empty SQLite database if not provided
RUN touch /app/trades.db

ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
