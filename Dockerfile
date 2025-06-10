FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        sqlite3 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Apple Silicon 向けにビルドする場合は下記のように `--platform` を指定してください
# docker build --platform linux/amd64 -t piphawk-ai:dev .

# 依存関係ファイルを先にコピーしてキャッシュを活用する
COPY pyproject.toml /app/pyproject.toml
COPY backend/requirements.txt /app/backend/requirements.txt

# 依存関係を先にインストール
RUN pip install --no-cache-dir -r backend/requirements.txt \
 && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.3.0

# アプリケーションコードを後からコピーしてレイヤーを分離
COPY . /app

# プロジェクトをインストール
RUN pip install --no-cache-dir .

# ensure logs directory exists
RUN mkdir -p /app/backend/logs

ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV PYTHONPATH=/app

CMD ["python", "-m", "piphawk_ai.main", "job"]
